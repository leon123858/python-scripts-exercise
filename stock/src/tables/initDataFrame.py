import pandas as pd
import twstock
from src.utils.tables import create_dataframe_from_lists


def get_stock_data(stock_id: str, start_year=None, start_month=None) -> pd.DataFrame:
    """
    獲取台股數據並返回 DataFrame

    Parameters:
    stock_id (str): 股票代碼 (例如: '2330')
    """
    stock = twstock.Stock(stock_id)

    if start_year is not None and start_month is not None:
        stock.fetch_from(start_year, start_month)
    elif start_year is None and start_month is None:
        stock.fetch_31()
    else:
        raise ValueError("should set year and month same time or not")

    df = create_dataframe_from_lists(
        stock.price,
        stock.high,
        stock.capacity,
        stock.change,
        stock.close,
        stock.date,
        stock.low,
        stock.open,
        stock.transaction,
        stock.turnover,
        columns=[
            "price",
            "high",
            "capacity",
            "change",
            "close",
            "date",
            "low",
            "open",
            "transaction",
            "turnover",
        ],
    )

    df.index = stock.date
    return df
