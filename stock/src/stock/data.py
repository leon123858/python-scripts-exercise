from collections.abc import Callable
from typing import Any

import pandas as pd
import twstock

from stock.utils.tables import create_dataframe_from_lists

StockFactory = Callable[[str], Any]


def get_stock_data(
    stock_id: str,
    start_year: int | None = None,
    start_month: int | None = None,
    stock_factory: StockFactory = twstock.Stock,
) -> pd.DataFrame:
    """Fetch stock price data and return it as a DataFrame."""
    if (start_year is None) != (start_month is None):
        raise ValueError("should set year and month same time or not")

    stock = stock_factory(stock_id)

    if start_year is not None and start_month is not None:
        stock.fetch_from(start_year, start_month)
    else:
        stock.fetch_31()

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
    df.index = pd.Index(stock.date)
    return df
