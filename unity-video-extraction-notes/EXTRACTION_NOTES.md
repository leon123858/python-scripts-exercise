# Unity 遊戲影片與獨立音訊提取筆記

以本次使用 `StreamEncrytor` 的遊戲為例，記錄從 Unity AssetBundle 還原可播放、有聲 MP4 的方法。

**適用範圍：目前只實測這一款遊戲。** 同公司其他作品可以沿用這套排查流程，但不能只因發行商或開發商相同，就假設混淆參數、檔名規則、Unity 版本和音訊對應完全一致。本筆記不推定未確認的公司名稱。

## 1. 核心結論

這款遊戲要分成兩件事處理：

1. 解開 bundle 的自訂循環 XOR 混淆，再提取 `VideoClip` 的原始影片資料。
2. 另外提取 `AudioClip`，把同一影片的 `role`、`other` 音軌混音，封裝回 MP4。

**單獨把 VideoClip 匯出成功，不代表已還原完整的有聲影片。** 本次原始 MP4 都沒有內嵌音軌；其中部分有 `tmcd` 時間碼資料串流，它不是聲音。

程式入口是 [main.py](main.py)，音訊流程在 [audio_pipeline.py](audio_pipeline.py)，一般使用方式見 [README.md](README.md)。

## 2. 先備妥哪些檔案

從遊戲安裝目錄保留以下資料及原始檔名、相對目錄：

```text
Game_Win_Data/
├─ il2cpp_data/Metadata/global-metadata.dat
└─ StreamingAssets/aa/
   ├─ catalog.json
   └─ StandaloneWindows64/
      ├─ sound_assets_..._role_<hash>.bundle
      ├─ sound_assets_..._other_<hash>.bundle
      └─ video_assets_assets/bundles/common/localvideos/
         ├─ album/
         ├─ chapter/
         ├─ chat/
         ├─ mainview/
         ├─ sceneplay/
         └─ story/chapter_*/
```

| 資料 | 用途 |
| --- | --- |
| `localvideos` 下的 bundle | 影片物件和原始 MP4 位元組 |
| `sound_assets_*.bundle` | 獨立聲音；只複製影片目錄會漏掉這些檔案 |
| `global-metadata.dat` | 尋找該遊戲的 XOR 混淆參數 |
| `catalog.json` | 取得 Addressables 的 bundle CRC，驗證還原是否正確 |

metadata、catalog 和 bundles 要來自同一遊戲版本。**不要先重新命名 bundle**：這個格式會使用檔名生成 XOR 序列，改名會使還原失敗。

撰寫本筆記時，工作目錄已不包含原始 `Game_Win_Data`；重新執行需補回來源，或透過命令列指定遊戲安裝位置。筆記中的結果來自先前已完成的實測與輸出清單。

## 3. 環境與執行方式

本專案使用 Python 3.13+、uv、UnityPy、lz4、pycryptodome，以及 PATH 上的 FFmpeg / ffprobe。實測的 Python 套件版本由 `uv.lock` 固定；UnityPy 的音訊轉換會使用其相依套件 `fmod_toolkit`。

```powershell
uv sync
ffmpeg -version
ffprobe -version

# 先試跑少量，再執行全部
uv run python main.py --limit 2
uv run python main.py
```

若遊戲資料在其他位置，必須一起指定影片、音訊、metadata 和 catalog，不能只改影片來源：

```powershell
$gameData = 'D:\Games\Example\Game_Win_Data'
$aa = Join-Path $gameData 'StreamingAssets\aa'
$bundleRoot = Join-Path $aa 'StandaloneWindows64'

uv run python main.py `
  --input "$bundleRoot\video_assets_assets\bundles\common\localvideos" `
  --audio-input "$bundleRoot" `
  --metadata "$gameData\il2cpp_data\Metadata\global-metadata.dat" `
  --catalog "$aa\catalog.json" `
  --output '.\extracted_videos' `
  --audio-output '.\extracted_videos_with_audio'
```

PowerShell 的續行反引號後方不能有空白。同公司另一款遊戲應使用新的輸出目錄，避免與已有清單、同名影片混在一起。

本次原始影片約 20.91 GB，有聲版約 21.15 GB；同時保留兩者需約 42 GB，再加上音訊暫存空間。程式逐個 bundle 處理，不必把全部資產載入記憶體。

## 4. 如何判斷 bundle 的混淆方式

### 不要只相信「加密」錯誤訊息

本次 bundle 開頭仍是 `UnityFS\0`，可讀到格式版本 8 和 Unity 版本 `2022.3.10f1`。但直接交給 UnityPy 時，會報「bundle 已加密，未提供金鑰」。

進一步檢查可見檔頭的解壓大小與 flags 明顯不合理。原因是 XOR 混淆破壞了這些欄位，讓 UnityPy 誤判為 Unity CN 加密；不是缺少一把 AES 金鑰。此專案的 pycryptodome 實際用在高速 XOR 運算，並不是用 AES 解開這些 bundle。

metadata 中可找到 `StreamEncrytor`、`KeyGenerator`、`XorStream`、`BUNDLE_ENCRYPT_OFFSET` 等名稱，與檔案的循環 XOR 特徵相符。這些是本次格式辨識的線索，不能單凭字串存在就認定解密成功。

### 本次驗證成立的還原公式

令：

- `S`：bundle 的原始檔名，僅移除最後的 `.bundle`，保留前面的 `.mp4`、底線和 hash。
- `H = SHA512(UTF8(S))`：64 bytes 的 digest。
- `L = 32 + (len(S) % 32)`：實際循環長度，介於 32 到 63。
- `M`：從該遊戲 metadata 找到的混淆參數陣列；本次長度為 35 bytes。
- `K[j] = H[j] XOR M[j % len(M)]`，其中 `0 <= j < L`。

對 bundle 的每個位元組，使用**從檔案開頭算起的絕對位置** `i`：

```text
i < 40：原樣保留
i >= 40：還原值 = 原檔值 XOR K[i % L]
```

兩個容易出錯的地方：

- 不是 `K[(i - 40) % L]`；40 只是開始混淆的位置，不是序列重新起算的位置。
- 長度不是把檔名長度限制到 64。檔名 stem 長度為 64 時，`L` 應回到 32；早期只測短影片檔名，便漏掉了這個音訊檔名會觸發的情況。

本次檔名皆為這種 ASCII 命名。遇到非 ASCII 檔名時，還要重新確認遊戲端如何計算字串長度和編碼。

### 從 metadata 尋找 `M`

本次 metadata 的 magic 是 `0xFAB11BAF`、版本是 29。`discover_mask()` 使用的方法是：

1. 讀取 metadata 的欄位預設值表與預設值資料區，取得候選初始資料的邊界。
2. 利用本次 UnityFS 檔頭中 offsets 50–63 原本應為零的對齊填充。
3. 已知填充的明文是零，因此該處的密文就是對應的 `K`。再與 `H` 做 XOR，可得到一段 `M` 的內容。
4. 在 metadata 資料區搜尋這段內容，並要求候選起點符合欄位初始資料邊界。
5. 試驗候選長度，還原 bundle 檔頭與 LZ4 目錄；後續再用整個 bundle 的 CRC 驗證。

目前實作讀取 metadata header 的 offsets 64、72，分別取得欄位預設值表、預設值資料區的 offset/size。這些 offset、UnityFS 的零填充區間，以及 flags `0x243` 的假設都屬於**這個版本的格式條件**，不是所有 Unity 遊戲的固定規則。

不需要把實際 `M` 寫死在腳本，也不要把本遊戲找到的位元組直接當成另一款遊戲的金鑰。

## 5. 提取影片：取資源範圍，不是更改副檔名

先還原整個 bundle，再交给 UnityPy。對每個 `VideoClip`，讀取 `m_ExternalResources` 的 `m_Source`、`m_Offset`、`m_Size`，從對應 resource 精確切出影片：

```python
import UnityPy
from UnityPy.helpers.ResourceReader import get_resource_data

# decoded_bundle 是已完成 XOR 還原、並通過 CRC 的 bundle bytes。
env = UnityPy.load(decoded_bundle)
for obj in env.objects:
    if obj.type.name != "VideoClip":
        continue
    clip = obj.read()
    resource = clip.m_ExternalResources
    video_bytes = get_resource_data(
        resource.m_Source,
        obj.assets_file,
        resource.m_Offset,
        resource.m_Size,
    )
    assert len(video_bytes) == resource.m_Size
    # 再按安全的輸出路徑寫入，不直接信任資產裡的任意路徑。
```

影片名稱優先取自 `m_OriginalPath`，目錄則保留來源 bundle 相對於 `localvideos` 的結構。原始 MP4 不重新編碼。

## 6. 提取與配對音訊

音訊 bundle 使用同一套 XOR 還原流程，也要驗證 catalog CRC。UnityPy 讀出 `AudioClip` 後，透過 `clip.samples` 取得可播放的解碼結果；本次取得的是 WAV。

目前確認的命名對應如下：

| 影片名稱 | 音訊資產名稱 |
| --- | --- |
| `video_10` | `video_10_role`、`video_10_other` |
| `scenenode_103` | `scenenode_103_role`、`scenenode_103_other` |
| `album_1` | `album_1_other` |
| `chat_video_1` | `chat_audio_1_role`、`chat_audio_1_other` |

`role`、`other` 是遊戲使用的音軌分類名稱。應把存在的對應音軌一起處理，不要只提取其中一條，也不要依相近編號猜測缺少的音訊。腳本另外核對 bundle 名稱和內部 `AudioClip.m_Name`，遇到同名多份候選會報錯。

只有影片、找不到對應聲音時，應記錄為 `missing_audio`。這不表示遊戲執行時一定沒有聲音：背景音樂或 UI 音效也可能由其他邏輯播放，只是不能在沒有對應依據時任意加入。

## 7. 混音、同步與 MP4 封裝

本專案依本次指定的處理方式，將音軌從時間 0 開始疊加，短音軌補靜音，超過影片長度的音訊裁掉。這是離線合併策略，不代表已還原遊戲內的動態音量、播放偏移、循環或互動停頓。

FFmpeg 流程的關鍵選項：

- `amix=...:normalize=0`：音軌等增益加總。
- `alimiter=limit=0.95:level=0:latency=1`：限制混音峰值，補償限制器延遲，不自動放大音量。
- `apad,atrim=duration=影片秒數`：補靜音或裁至影片長度。
- `-c:v copy`：只複製影片串流，畫面不重新編碼。
- `-c:a aac -b:a 192k -ar 48000`：聲音編碼為一般播放器容易支援的 AAC。

這不是整份檔案的無損轉換：**畫面不重編碼，聲音有重新編碼。**

```powershell
# 預設方式：直接從 0 秒合併，裁補音訊
uv run python main.py --audio-only --duration-policy fit

# 另一款遊戲尚未確認同步時，可先採保守方式
uv run python main.py --audio-only --duration-policy strict `
  --audio-output '.\audio_review_output'
```

`--audio-only` 需要已有原始影片及其 manifest，並會檢查來源和輸出雜湊。`strict` 會將時長差超過 0.5 秒的音軌另存 `_audio_review/`，標示 `needs_sync`，不自動猜測同步；要對已有有聲檔重新採用這個政策，使用新的輸出目錄。

## 8. 怎樣才算驗證成功

| 檢查 | 能確認什麼 |
| --- | --- |
| UnityFS 檔頭、LZ4 目錄可解析 | 還原方式基本合理，尚不足以證明整包正確 |
| 解壓後全部 bundle blocks 的 CRC32 與 catalog 相同 | 整包還原內容與遊戲提供的 CRC 相符；不是只算 MP4 的 CRC |
| 資源長度、寫入前後 SHA-256 相同 | 匯出範圍與檔案寫入沒有截斷或改動 |
| ffprobe 看到影片和音訊串流 | 有聲版本確實有音軌，不只是能打開的無聲 MP4 |
| FFmpeg 完整解碼輸出音軌 | 音訊可解碼，沒有解碼錯誤 |
| 影片串流 hash 比對 | 抽查合併前後的壓縮畫面資料相同 |
| 播放或音量抽查 | 有聲音內容，而非只有一條全靜音的音軌 |

本次沒有逐幀解碼全部影片，也沒有人工逐支核對口型；CRC、雜湊和解碼檢查不能替代對遊戲時間軸的理解。

本次實測結果：

- 790 個影片 bundle，成功匯出 790 支原始影片。
- 提取並使用 1,547 條獨立音軌，產生 776 支有聲影片。
- 20 支影片的音訊時長有較大差異，已依指定方式從 0 秒裁補。
- 14 支未找到配對音訊，包括 6 支章節封面、3 支主畫面背景，以及 `video_13`、`video_905_2`、`video_1017`、`video_1074`、`video_1089`。
- 最終沒有處理錯誤，但有聲清單的 `complete` 仍為 false，因為那 14 支未被補成有聲影片。

查看 `extracted_videos_with_audio/audio_summary.txt` 可快速讀取例外清單；`manifest.json` 則保存來源、CRC、雜湊、音軌和影音資訊，供續跑與追查。

## 9. 常見失敗與排查方向

| 現象 | 優先檢查 |
| --- | --- |
| UnityPy 說需要 AssetBundle 解密金鑰 | 檔頭是否已被自訂混淆，不能直接認定是 Unity CN AES |
| 影片可還原，較長檔名的音訊失敗 | 循環長度是否正確使用 `32 + len(stem) % 32`，以及 bundle 是否被改名 |
| 能解析檔頭，但 CRC 不相符 | 參數、絕對位置索引、檔名、來源版本或資料完整性是否有誤 |
| MP4 有畫面沒有聲音 | 是否漏掉獨立 sound bundles；`tmcd` 不是音訊 |
| 有聲音但長短、口型不一致 | 同名不等於一定從 0 秒同步；檢查遊戲設定、播放偏移或採 `strict` 留待確認 |
| `Existing output differs` | 不覆寫不明同名檔；另選輸出目錄或先移開舊檔 |
| 找不到 metadata 或影片來源 | 補回原始資料，或完整指定四種來源路徑 |

## 10. 換到同公司另一款遊戲的檢查順序

1. 先找影片、音訊、metadata、catalog，確認來自同一版本，保存原始檔名。
2. 抽查小型 bundle 的 signature、UnityFS / Unity 版本及檔頭欄位。
3. 若直接使用 UnityPy 失敗，先辨別真正的加密或混淆方式，不直接套用錯誤訊息建議。
4. 確認 metadata 版本、混淆起點、SHA 輸入、循環長度、索引位置及參數來源；以 catalog CRC 驗證候選方案。
5. 同時測試短、長檔名，以及影片和音訊 bundle；只測一支影片不夠。
6. 提取一組畫面及所有對應音軌，核對命名、片長、實際聲音和同步方式。
7. 確認小樣本成功後才全量處理，保存每個來源的成功、缺音訊、需同步或失敗狀態。

目前工具只支援已驗證的這套格式。遇到其他 UnityFS flags、metadata 版本或音訊命名方式，應先調整與驗證解析器，而不是放寬錯誤檢查，讓未正確還原的資料被當成成功。
