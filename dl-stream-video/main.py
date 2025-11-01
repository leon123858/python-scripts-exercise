#!/usr/bin/env python
# coding: utf-8

# In[32]:


import json

# --- !!! 關鍵步驟 !!! ---
# 你必須在這裡填入正確的參數
PARAMETER_PATH = "parameters.json"

try:
    with open(PARAMETER_PATH, 'r', encoding='utf-8') as file:
        para_data = json.load(file)
        print("檔案讀取並解析成功！")

except FileNotFoundError:
    print(f"錯誤：找不到檔案 '{PARAMETER_PATH}'。請確保檔案在同一個資料夾中。")
except json.JSONDecodeError:
    print(f"錯誤：檔案 '{PARAMETER_PATH}' 不是一個有效的 JSON 格式。")
except Exception as e:
    print(f"讀取時發生未預期的錯誤: {e}")


# In[33]:


from typing import Optional, Any  # 導入型別提示工具

def download_json_file(url: str) -> Optional[Any]:
    """
    從指定的 URL 下載 JSON 檔案並將其解析為 Python 物件。

    參數:
        url (str): 要下載的 JSON 檔案的完整 URL。

    回傳:
        Optional[Any]:
            - 成功: 回傳解析後的 Python 物件 (通常是 dict 或 list)。
            - 失敗: 回傳 None。
    """
    print(f"準備下載: {url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # 失敗 (非 2xx) 則引發 RequestException
        print("下載成功，正在解析 JSON...")

        data_res = response.json()
        print("JSON 解析成功。")

        return data_res

    except requests.exceptions.RequestException as e:
        print(f"[下載失敗] 請求時發生錯誤: {e}")
        return None  # 失敗，回傳 None
    except requests.exceptions.JSONDecodeError:
        print(f"錯誤：下載的內容不是有效的 JSON 格式。")
        return None  # 失敗，回傳 None


# In[34]:


from typing import Optional
import concurrent.futures

def get_video_by_stream(server_url: str,
                                 play_list_url: str,
                                 stream_index: int,
                                 tmp_file: str = "restored_video.mp4",
                                 max_workers: int = 4) -> Optional[str]:
    """
    下載指定的影片流 (DASH) 並將其合併為單一檔案。
    使用 ThreadPoolExecutor 平行下載片段以加速。

    參數:
        max_workers (int): 同時下載的最大執行緒數量。
    """

    if not server_url:
        print("錯誤：'server_url' (伺服器位址) 不得為空。")
        return None

    data = download_json_file(play_list_url)
    if not data:
        print(f"錯誤：無法從 {play_list_url} 下載或解析播放列表。")
        return None

    try:
        # sort video by stream size
        video_stream_list = sorted(
            data['video'],
            key=lambda item: item['width'] * item['height'],
            reverse=True
        )
        video_stream = video_stream_list[stream_index]
        print(f"已選擇影片流: {video_stream['width']}x{video_stream['height']} @ {video_stream['bitrate']} bps")

        print("正在解碼 Init Segment...")
        init_segment_b64 = video_stream['init_segment']
        init_data = base64.b64decode(init_segment_b64)

        with open(tmp_file, 'wb') as f:
            f.write(init_data)
        print(f"已寫入 Init Segment 到 {tmp_file}")

        segments = video_stream['segments']
        total_segments = len(segments)
        print(f"準備平行下載 {total_segments} 個影片片段 (使用 {max_workers} 個 workers)...")

        urls_to_download = [f"{server_url}/{segment['url']}" for segment in segments]

        session = requests.Session()

        # 定義單個下載任務
        def download_segment(url: str) -> Optional[bytes]:
            try:
                # 使用 session.get 而非 requests.get
                res = session.get(url, timeout=10)
                res.raise_for_status()
                return res.content
            except requests.exceptions.RequestException as e:
                print(f"\n[下載失敗] 片段 {url} 錯誤: {e}")
                return None # 標記失敗

        # 使用 'ab' (append binary) 模式來附加檔案
        with open(tmp_file, 'ab') as f:
            # 建立執行緒池
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = executor.map(download_segment, urls_to_download)

                for i, segment_content in enumerate(results):

                    if segment_content is None:
                        # 如果任何一個片段下載失敗 (download_segment 回傳 None)
                        print(f"\n錯誤：片段 {i+1} 下載失敗，還原中止。")
                        return None # 中止函式

                    f.write(segment_content)

                    progress = (i + 1) / total_segments
                    print(f"  已寫入片段 {i+1}/{total_segments} ({progress:.1%})", end='\r', flush=True)

        print(f"\n影片還原完成！已儲存為 {tmp_file}")
        return tmp_file  # 成功，回傳檔案路徑

    except (TypeError, KeyError, IndexError) as e:
        print(f"錯誤：JSON 資料結構不符預期 (例如找不到 'video' 或索引 {stream_index} 無效)。")
        print(f"詳細錯誤: {e}")
        return None
    except IOError as e:
        print(f"錯誤：寫入檔案 '{tmp_file}' 失敗。請檢查權限或磁碟空間。")
        print(f"詳細錯誤: {e}")
        return None
    except Exception as e:
        print(f"發生未預期的錯誤: {e}")
        return None


# In[35]:


import requests
import base64
from typing import Optional
import concurrent.futures

def get_audio_by_stream(server_url: str,
                                 play_list_url: str,
                                 stream_index: int,
                                 tmp_file: str = "restored_audio.m4a",
                                 max_workers: int = 10) -> Optional[str]:
    """
    下載指定的聲音流 (DASH) 並將其合併為單一檔案。
    使用 ThreadPoolExecutor 平行下載片段以加速。
    """
    if not server_url:
        print("錯誤：'server_url' (伺服器位址) 不得為空。")
        return None

    data = download_json_file(play_list_url)
    if not data:
        print(f"錯誤：無法從 {play_list_url} 下載或解析播放列表。")
        return None

    try:
        target_key = 'audio'
        if target_key not in data or not data[target_key]:
            print(f"錯誤：在 JSON 檔案中找不到 '{target_key}' 陣列或陣列為空。")
            return None

        audio_stream = data[target_key][stream_index]
        print(f"已選擇聲音流: Codec: {audio_stream.get('codecs', 'N/A')}, Bitrate: {audio_stream.get('bitrate', 'N/A')} bps")

        print("正在解碼 Init Segment...")
        init_segment_b64 = audio_stream['init_segment']
        init_data = base64.b64decode(init_segment_b64)

        with open(tmp_file, 'wb') as f:
            f.write(init_data)
        print(f"已寫入 Init Segment 到 {tmp_file}")

        segments = audio_stream['segments']
        total_segments = len(segments)
        print(f"準備平行下載 {total_segments} 個聲音片段 (使用 {max_workers} 個 workers)...")

        urls_to_download = [f"{server_url}/{segment['url']}" for segment in segments]

        session = requests.Session()

        def download_segment(url: str) -> Optional[bytes]:
            try:
                res = session.get(url, timeout=10)
                res.raise_for_status()
                return res.content
            except requests.exceptions.RequestException as e:
                print(f"\n[下載失敗] 片段 {url} 錯誤: {e}")
                return None

        # 使用 'ab' (append binary) 模式來附加檔案
        with open(tmp_file, 'ab') as f:
            # 建立執行緒池
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = executor.map(download_segment, urls_to_download)

                # 依序寫入
                for i, segment_content in enumerate(results):
                    if segment_content is None:
                        print(f"\n錯誤：片段 {i+1} 下載失敗，還原中止。")
                        return None

                    f.write(segment_content)

                    progress = (i + 1) / total_segments
                    print(f"  已寫入片段 {i+1}/{total_segments} ({progress:.1%})", end='\r', flush=True)

        print(f"\n聲音還原完成！已儲存為 {tmp_file}")
        return tmp_file  # 成功，回傳檔案路徑

    # 7. 處理所有潛在的錯誤 (同上)
    except (TypeError, KeyError, IndexError) as e:
        print(f"錯誤：JSON 資料結構不符預期 (例如找不到 'audio' 或索引 {stream_index} 無效)。")
        print(f"詳細錯誤: {e}")
        return None
    except IOError as e:
        print(f"錯誤：寫入檔案 '{tmp_file}' 失敗。請檢查權限或磁碟空間。")
        print(f"詳細錯誤: {e}")
        return None
    except Exception as e:
        print(f"發生未預期的錯誤: {e}")
        return None


# In[36]:


import subprocess  # 用於執行外部指令
import shutil      # 用於檢查 ffmpeg 指令是否存在

def merge_video_and_audio(video_in: str, audio_in: str, output_file: str) -> bool:
    """
    使用 FFmpeg 將指定的影像和聲音檔案合併 (mux)。

    參數:
        video_in (str): 輸入的影像檔案路徑。
        audio_in (str): 輸入的聲音檔案路徑。
        output_file (str): 合併後的輸出檔案路徑。

    回傳:
        bool: 成功則回傳 True，失敗則回傳 False。
    """

    # 1. 檢查 FFmpeg 是否存在於系統路徑中
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        print("\n--- 錯誤：找不到 'ffmpeg' ---")
        print("此腳本需要 FFmpeg 才能合併影音。")
        print("請先安裝 FFmpeg 並確保它在您的系統 PATH 環境變數中。")
        print("您可以從官網下載: https://ffmpeg.org/download.html")
        print("------------------------------")
        return False  # 失敗，回傳 False

    print(f"已在 '{ffmpeg_path}' 找到 FFmpeg。")

    # 2. 檢查輸入檔案是否存在
    if not os.path.exists(video_in):
        print(f"錯誤：找不到影像檔案 '{video_in}'。")
        return False  # 失敗，回傳 False

    if not os.path.exists(audio_in):
        print(f"錯誤：找不到聲音檔案 '{audio_in}'。")
        return False  # 失敗, 回傳 False

    print(f"正在嘗試合併 '{video_in}' 和 '{audio_in}'...")

    # 3. 建立要執行的 FFmpeg 指令
    command = [
        ffmpeg_path,
        '-i', video_in,     # 輸入檔案1 (影像)
        '-i', audio_in,     # 輸入檔案2 (聲音)
        '-c', 'copy',       # 參數: 'copy' 表示直接複製，不重新編碼 (速度最快)
        '-y',               # 參數: 如果輸出檔案已存在，自動覆蓋
        output_file         # 輸出檔案名稱
    ]

    print(f"正在執行指令: {' '.join(command)}")

    try:
        # 4. 執行指令
        # check=True: 如果 FFmpeg 失敗 (回傳非 0 代碼)，Python 會引發錯誤
        # capture_output=True: 捕獲 FFmpeg 的所有標準輸出和錯誤訊息
        # text=True: 將捕獲的輸出解碼為文字
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')

        print("\n=========================")
        print(" 合併成功！ ")
        print(f" 檔案已儲存為: {output_file} ")
        print("=========================")

        # (優化：成功時不需要顯示 ffmpeg 的完整日誌，它通常是雜訊)
        # (如果需要除錯，可以取消下面這行的註解)
        # print("\n--- FFmpeg 詳細日誌 (stderr) ---")
        # print(result.stderr)

        return True  # 成功，回傳 True

    except subprocess.CalledProcessError as e:
        # 如果 FFmpeg 執行出錯
        print(f"\n--- FFmpeg 執行失敗 (錯誤碼: {e.returncode}) ---")
        print("FFmpeg 錯誤訊息 (stderr):")
        print(e.stderr)  # 顯示 FFmpeg 傳回的錯誤訊息
        print("-----------------------------------------")
        return False  # 失敗，回傳 False

    except FileNotFoundError:
        # 如果 'ffmpeg' 指令本身找不到 (雖然 shutil.which 應該已處理)
        print(f"錯誤：找不到指令 '{ffmpeg_path}'。請檢查您的安裝或 PATH。")
        return False  # 失敗，回傳 False


# In[ ]:


import os

print("--- 準備開始執行下載與合併任務 ---")

# 檢查 'para_data' 變數是否存在 (由第一個 Cell 載入)
if 'para_data' in locals() and para_data:
    print(f"已成功從 '{PARAMETER_PATH}' 讀取參數。")

    # 1. 檢查 'download_jobs' 鍵是否存在
    if 'download_jobs' not in para_data or not isinstance(para_data['download_jobs'], list):
        print(f"錯誤：參數檔案中必須包含一個名為 'download_jobs' 的 [列表] (List)。")
        jobs = []
    else:
        jobs = para_data['download_jobs']

    # 2. 循環執行所有下載任務
    total_jobs = len(jobs)
    print(f"\n偵測到 {total_jobs} 個下載任務，準備開始執行...")

    for i, job in enumerate(jobs):
        job_name = job.get('job_name', f'未命名任務 {i+1}')
        print(f"\n=========================================")
        print(f"== 任務 {i+1}/{total_jobs}: {job_name} ==")
        print(f"=========================================")

        try:
            # --- 獲取任務參數 ---
            server_url = job['server_url']
            playlist_url = job['playlist_url']
            video_index = job['video_stream_index']
            audio_index = job['audio_stream_index']
            output_file = job['final_output_file']

            # (我們使用您函式中預設的暫存檔名)
            temp_video_file = "restored_video.mp4"
            temp_audio_file = "restored_audio.m4a"

            # --- 步驟 A: 下載影片 ---
            print(f"\n--- 步驟 A: 開始下載影片 (索引 {video_index}) ---")

            video_file_path = get_video_by_stream(
                server_url=server_url,
                play_list_url=playlist_url,
                stream_index=video_index,
                tmp_file=temp_video_file,
                max_workers=4
            )

            if not video_file_path:
                print(f"任務 '{job_name}' 失敗：下載影片時出錯。跳過此任務。")
                continue # 跳到下一個 for 迴圈

            # --- 步驟 B: 下載聲音 ---
            print(f"\n--- 步驟 B: 開始下載聲音 (索引 {audio_index}) ---")

            audio_file_path = get_audio_by_stream(
                server_url=server_url,
                play_list_url=playlist_url,
                stream_index=audio_index,
                tmp_file=temp_audio_file,
                max_workers=4
            )

            if not audio_file_path:
                print(f"任務 '{job_name}' 失敗：下載聲音時出錯。跳過此任務。")
                # (清理已下載的影片暫存檔)
                if os.path.exists(video_file_path):
                    print(f"正在清理影片暫存檔: {video_file_path}")
                    os.remove(video_file_path)
                continue # 跳到下一個 for 迴圈

            # --- 步驟 C: 合併影音 ---
            print(f"\n--- 步驟 C: 開始合併影音至 {output_file} ---")

            merge_success = merge_video_and_audio(
                video_in=video_file_path,
                audio_in=audio_file_path,
                output_file=output_file,
            )

            # --- 步驟 D: 清理暫存檔 (如果合併成功) ---
            if merge_success:
                print(f"\n--- 步驟 D: 合併成功，清理暫存檔 ---")
                try:
                    os.remove(video_file_path)
                    print(f"已刪除: {video_file_path}")
                    os.remove(audio_file_path)
                    print(f"已刪除: {audio_file_path}")
                except OSError as e:
                    print(f"刪除暫存檔 {video_file_path} 或 {audio_file_path} 失敗: {e}")
            else:
                print(f"\n任務 '{job_name}' 失敗：合併影音時出錯。")
                print(f"暫存檔 {video_file_path} 和 {audio_file_path} 已保留，供除錯使用。")

        except KeyError as e:
            print(f"\n任務 '{job_name}' 失敗：'parameters.json' 中缺少必要的鍵 (Key): {e}")
            print("請檢查 JSON 檔案是否包含 'server_url', 'playlist_url', 'video_stream_index', 'audio_stream_index', 'final_output_file'")
        except Exception as e:
            print(f"\n執行任務 '{job_name}' 時發生未預期的錯誤: {e}")

        print(f"--- 任務: {job_name} 處理完畢 ---")

    print("\n=========================================")
    print("== 所有任務執行完畢 ==")
    print("=========================================")

else:
    print("錯誤：找不到 'para_data' 變數。")
    print("請確保您已經成功執行 [第一個] 讀取 JSON 檔案的儲存格 (Cell)。")

