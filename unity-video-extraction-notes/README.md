# Unity 影片還原工具

格式分析、還原原理與套用到同公司其他遊戲的步驟，見 [影片與音訊提取筆記](EXTRACTION_NOTES.md)。

將本遊戲 `localvideos` 下的 Unity AssetBundle 還原成影片，再提取對應的獨立 AudioClip、混音並封裝為有聲 MP4。保留目錄與影片名稱；畫面不重新編碼，音訊轉為 AAC。不修改遊戲資產或存檔。

## 執行

需要 Python 3.13+、uv，以及 PATH 上可執行的 `ffmpeg`、`ffprobe`。

```powershell
uv sync
uv run python main.py
```

預設影片來源為 `Game_Win_Data/StreamingAssets/aa/StandaloneWindows64/video_assets_assets/bundles/common/localvideos`，音訊來源為 `StandaloneWindows64` 下的 `sound_assets_*.bundle`。原始無聲影片保留於 `extracted_videos/`，**請播放 `extracted_videos_with_audio/` 裡的有聲版本**。

```powershell
# 小量試跑
uv run python main.py --limit 2

# 自訂路徑
uv run python main.py --input "遊戲的 localvideos 目錄" --output "影片輸出目錄" --metadata "global-metadata.dat" --catalog "catalog.json"

# 指定獨立音訊來源和有聲影片輸出
uv run python main.py --audio-input "StandaloneWindows64 目錄" --audio-output "有聲影片輸出目錄"

# 僅提取原始無聲影片
uv run python main.py --video-only

# 已經提取過畫面時，只重跑音訊流程（仍會檢查來源與原始影片雜湊）
uv run python main.py --audio-only

# 可選：時長差超過 0.5 秒時另存完整音轨、暫不合併
uv run python main.py --audio-only --duration-policy strict
```

預設 metadata 位於 `Game_Win_Data/il2cpp_data/Metadata/global-metadata.dat`，catalog 位於 `Game_Win_Data/StreamingAssets/aa/catalog.json`。所有預設路徑以程式所在目錄為基準。

## 還原與驗證

此遊戲使用自訂 StreamEncrytor 循環 XOR 混淆，而非 UnityPy 原先錯誤訊息所指的 Unity CN AES 加密。工具從 IL2CPP metadata v29 的欄位初始資料找出混淆參數，依 bundle 檔名產生 XOR 序列，保留前 40 bytes，再以 UnityPy 讀取 VideoClip 及其 resource。金鑰只保留於記憶體，不寫入程式或清單。

每個 bundle 都檢查解壓後資料的 CRC32，必須與遊戲 Addressables catalog 的 CRC 一致。影片按資源 offset/size 原樣取出，再檢查寫入檔案的 SHA-256 與大小，最後由 ffprobe 確認影片串流及正值片長。ffprobe 屬於容器與串流辨識檢查，並未逐幀解碼全片；來源 CRC 提供還原內容完整性的檢查。

`extracted_videos/manifest.json` 記錄原始影片提取；它的成功狀態只代表畫面資料。`extracted_videos_with_audio/manifest.json` 另記錄音訊來源、CRC、SHA-256、音軌時長差、輸出影音資訊與未配對項目。有聲流程完整成功回傳 0；處理失敗回傳 1；只有未找到音訊或需人工同步的項目時回傳 2。有聲清單的 `summary.complete` 只有全部影片都有音訊且成功才為 true。

## 音訊對應與合併

工具以完整名稱精確配對 `影片名_role`、`影片名_other`，聊天影片使用 `chat_video_N` → `chat_audio_N` 的對應；不以近似數字猜測。每個音訊 bundle 都驗證 catalog CRC，再由 UnityPy/FMOD 解碼。兩條完整音軌從時間 0 同步混音，使用等增益加總與具延遲補償的峰值限制器防止爆音；輸出 AAC 192 kbps / 48 kHz，影片使用 stream copy。這不是遊戲執行時音量設定的逐一重建。

依使用者指定，預設 `--duration-policy fit`：所有音軌从第 0 秒開始，短音軌在尾端補靜音，超出影片的音訊裁掉；不拉伸聲音，亦不改變畫面。時長差超過 0.5 秒的影片在清單標示 `duration_adjusted: true`。可選 `--duration-policy strict` 將這些例外的完整音軌另存 `_audio_review/` 並標示 `needs_sync`。此選項不會撤回已完成的有聲檔；要重新套用保守政策請指定新的 `--audio-output`。

合併後確認音訊串流、片長及畫面規格，並完整解碼輸出音軌檢查錯誤。沒有配對音軌的影片只保留在原始目錄，列為 `missing_audio`，不放入有聲目錄冒充成功；遊戲另外即時播放的 UI 音效或背景音樂也不會任意加進影片。

中斷後執行相同指令即可繼續。程式重新核對已有來源和輸出雜湊，並再次執行 ffprobe；尚未記錄於清單但與還原資料一致的影片也可沿用。不同內容的同名檔案不會被覆寫，請先將衝突檔移到其他位置再重跑。寫入過程使用 `.part` 暫存檔；影片通過檢查才改為正式檔名。請勿同時啟動兩個程序寫入同一輸出目錄。

這是針對本遊戲檔案格式的工具，不是通用 Unity 解密器；不相符的 metadata、catalog 或 bundle 格式會明確失敗。原始影片約 21 GB，有聲版本另需約 21 GB，執行時另需單一 bundle 的解壓記憶體與當前影片的音訊暫存空間。兩個輸出目錄都支援透過清單與雜湊續跑。

## 測試

```powershell
uv run python -m unittest discover -s tests -v
```
