import pandas as pd


def create_dataframe_from_lists(*args, columns=None) -> pd.DataFrame:
    """
    將多個 List 轉換成 DataFrame

    Parameters:
    *args: 多個列表
    columns: 欄位名稱列表

    Returns:
    pandas.DataFrame: 轉換後的數據表格
    """
    # 檢查所有列表長度是否相同
    lengths = [len(lst) for lst in args]
    if len(set(lengths)) != 1:
        raise ValueError("all list len should same")

    if columns is None:
        raise ValueError("should have col name")

    if len(columns) != len(args):
        raise ValueError("col name len not right")

    df = pd.DataFrame(dict(zip(columns, args)))
    return df
