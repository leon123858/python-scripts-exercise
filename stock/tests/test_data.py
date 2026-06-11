import datetime as dt

import pandas as pd
import pytest

from stock.data import get_stock_data


class FakeStock:
    def __init__(self, stock_id: str) -> None:
        if stock_id == "9999":
            raise KeyError(stock_id)
        self.sid = stock_id
        self.price = [10.0, 12.0]
        self.high = [11.0, 13.0]
        self.capacity = [100, 200]
        self.change = [0.5, 1.0]
        self.close = [10.5, 12.5]
        self.date = [dt.date(2023, 1, 1), dt.date(2023, 1, 2)]
        self.low = [9.5, 11.5]
        self.open = [10.0, 12.0]
        self.transaction = [5, 6]
        self.turnover = [1000, 2000]
        self.fetch_from_args: tuple[int, int] | None = None
        self.fetch_31_called = False

    def fetch_from(self, year: int, month: int) -> None:
        self.fetch_from_args = (year, month)

    def fetch_31(self) -> None:
        self.fetch_31_called = True


def test_get_stock_data_fetches_recent_data_by_default():
    stocks: list[FakeStock] = []

    def stock_factory(stock_id: str) -> FakeStock:
        stock = FakeStock(stock_id)
        stocks.append(stock)
        return stock

    df = get_stock_data("2330", stock_factory=stock_factory)

    assert stocks[0].fetch_31_called is True
    assert df.shape == (2, 10)
    assert df["price"].tolist() == [10.0, 12.0]
    assert list(df.index) == list(pd.to_datetime(stocks[0].date))


def test_get_stock_data_fetches_from_year_and_month():
    stocks: list[FakeStock] = []

    def stock_factory(stock_id: str) -> FakeStock:
        stock = FakeStock(stock_id)
        stocks.append(stock)
        return stock

    get_stock_data("2330", 2023, 1, stock_factory=stock_factory)

    assert stocks[0].fetch_from_args == (2023, 1)
    assert stocks[0].fetch_31_called is False


def test_get_stock_data_validates_partial_date_before_fetching():
    def stock_factory(stock_id: str) -> FakeStock:
        raise AssertionError("stock factory should not be called")

    with pytest.raises(ValueError, match="should set year and month same time or not"):
        get_stock_data("2330", 2023, stock_factory=stock_factory)


def test_get_stock_data_preserves_stock_factory_errors():
    with pytest.raises(KeyError, match="9999"):
        get_stock_data("9999", stock_factory=FakeStock)
