from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd
import twstock

from stock.utils.tables import create_dataframe_from_lists

StockFactory = Callable[[str], Any]
STANDARD_COLUMNS = [
    "date",
    "open",
    "high",
    "low",
    "close",
    "price",
    "volume",
    "turnover",
    "change",
    "transaction",
]
DEFAULT_CACHE_DIR = Path("data/cache")


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
        stock.date,
        stock.open,
        stock.high,
        stock.low,
        stock.close,
        stock.price,
        stock.capacity,
        stock.turnover,
        stock.change,
        stock.transaction,
        columns=[
            "date",
            "open",
            "high",
            "low",
            "close",
            "price",
            "volume",
            "turnover",
            "change",
            "transaction",
        ],
    )
    return normalize_price_data(df)


def normalize_price_data(data: pd.DataFrame) -> pd.DataFrame:
    normalized = data.copy().reset_index(drop=True)
    if "capacity" in normalized.columns and "volume" not in normalized.columns:
        normalized = normalized.rename(columns={"capacity": "volume"})
    missing = set(STANDARD_COLUMNS) - set(normalized.columns)
    if missing:
        raise ValueError(f"stock data missing columns: {sorted(missing)}")
    normalized = normalized[STANDARD_COLUMNS]
    normalized["date"] = pd.to_datetime(normalized["date"])
    normalized = normalized.sort_values("date").reset_index(drop=True)
    normalized.index = pd.Index(normalized["date"])
    normalized.index.name = None
    return normalized


def _cache_path(stock_id: str, cache_dir: str | Path = DEFAULT_CACHE_DIR) -> Path:
    return Path(cache_dir) / f"{stock_id}.csv"


def _covers_requested_period(
    data: pd.DataFrame, start_year: int | None, start_month: int | None
) -> bool:
    if data.empty:
        return False
    if start_year is None and start_month is None:
        return True
    start_date = pd.Timestamp(year=start_year or 1, month=start_month or 1, day=1)
    return pd.Timestamp(data["date"].min()) <= start_date


def _filter_requested_period(
    data: pd.DataFrame, start_year: int | None, start_month: int | None
) -> pd.DataFrame:
    if start_year is None and start_month is None:
        return data
    start_date = pd.Timestamp(year=start_year or 1, month=start_month or 1, day=1)
    return normalize_price_data(data[data["date"] >= start_date])


def read_cached_stock_data(
    stock_id: str,
    cache_dir: str | Path = DEFAULT_CACHE_DIR,
) -> pd.DataFrame | None:
    path = _cache_path(stock_id, cache_dir)
    if not path.exists():
        return None
    return normalize_price_data(pd.read_csv(path))


def write_cached_stock_data(
    stock_id: str,
    data: pd.DataFrame,
    cache_dir: str | Path = DEFAULT_CACHE_DIR,
) -> Path:
    path = _cache_path(stock_id, cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalize_price_data(data).to_csv(path, index=False)
    return path


def get_stock_data_cached(
    stock_id: str,
    start_year: int | None = None,
    start_month: int | None = None,
    cache_dir: str | Path = DEFAULT_CACHE_DIR,
    stock_factory: StockFactory = twstock.Stock,
    refresh: bool = False,
) -> pd.DataFrame:
    if (start_year is None) != (start_month is None):
        raise ValueError("should set year and month same time or not")

    if not refresh:
        cached = read_cached_stock_data(stock_id, cache_dir)
        if cached is not None and _covers_requested_period(
            cached, start_year, start_month
        ):
            return _filter_requested_period(cached, start_year, start_month)

    data = get_stock_data(
        stock_id,
        start_year=start_year,
        start_month=start_month,
        stock_factory=stock_factory,
    )
    write_cached_stock_data(stock_id, data, cache_dir)
    return data
