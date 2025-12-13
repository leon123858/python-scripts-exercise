import pandas as pd


def process_ethereum_logs(file_path):
    # 1. 定義欄位名稱
    # 原始數據的 "block_time" 包含空格 (例如: 2025-11-24 22:18:11 UTC)
    # read_csv 遇到空格會切分，所以我們手動定義 date, time, tz 三個欄位來接住它
    cols = ['date', 'time', 'tz', 'topic1', 'topic2', 'topic3', 'tx_hash']

    try:
        # 2. 讀取 data.txt
        # sep=r'\s+' 表示以任意數量的空格或 Tab 作為分隔符
        # skiprows=1 表示跳過原本檔案裡的第一行標題 (因為我們要用自定義的 cols)
        df = pd.read_csv(file_path, sep=r'\s+', skiprows=1, names=cols)
    except FileNotFoundError:
        print(f"錯誤: 找不到檔案 {file_path}，請確認檔案位置。")
        return

    # 3. 輔助函數：清洗數據
    def decode_address(hex_str):
        # 處理可能的 NaN 或非字串情況
        if not isinstance(hex_str, str): return hex_str
        # 取最後 40 個字元 (20 bytes) 並補回 0x
        return '0x' + hex_str[-40:]

    def decode_int(hex_str):
        # 將 Hex 轉為十進位整數
        try:
            return int(hex_str, 16)
        except (ValueError, TypeError):
            return 0

    # 4. 應用轉換邏輯
    # 合併時間欄位
    df['block_time'] = pd.to_datetime(df['date'] + ' ' + df['time'])

    # 解析地址 (Topic1, Topic2)
    df['topic1_parsed'] = df['topic1'].apply(decode_address)
    df['topic2_parsed'] = df['topic2'].apply(decode_address)

    # 解析數值 (Topic3)
    df['topic3_decimal'] = df['topic3'].apply(decode_int)

    # 5. 整理最終輸出表格
    # 只選取處理好的欄位，並重新排序
    final_view = df[['block_time', 'topic1_parsed', 'topic2_parsed', 'topic3_decimal', 'tx_hash']]

    return final_view


# 執行主程式
if __name__ == "__main__":
    result_df = process_ethereum_logs('data.txt')

    # 不同费率的流动资金池数量
    q1_ret = result_df.groupby("topic3_decimal").count().reset_index()
    print(q1_ret.head(10))

    # 按周汇总的新建流动资金池总数
    q2_ret = result_df.copy()
    q2_ret['block_time'] = q2_ret['block_time'].dt.isocalendar().week
    q2_ret = q2_ret.groupby('block_time').count().reset_index()
    print(q2_ret.head())

    #每日新建流动资金池总数
    q3_ret = result_df.copy()
    q3_ret['date_str'] = q3_ret['block_time'].dt.strftime('%Y-%m-%d')
    q3_ret = q3_ret.groupby('date_str').count().reset_index()
    print(q3_ret.head())

    # 统计资金池数量最多的代币Token
    part1 = result_df[['tx_hash', 'topic1_parsed']].rename(columns={'topic1_parsed': 'token'})
    part2 = result_df[['tx_hash', 'topic2_parsed']].rename(columns={'topic2_parsed': 'token'})
    q4_ret = pd.concat([part1, part2], ignore_index=True)
    q4_ret = q4_ret.groupby('token').count().reset_index()
    print(q4_ret.sort_values("tx_hash", ascending=False).head(20))

    # 最新的100个流动资金池记录
    q5_ret = result_df.sort_values("block_time", ascending=False).head(20)
    print(q5_ret.head(20))