import datetime as dt

import pandas as pd
import pytest

from stock import BaseStrategy
from stock.backtest import run_daily_backtest
from stock.core import StrategyContext
from stock.data import get_stock_data_cached, normalize_price_data
from stock.indicators import moving_average, returns, rsi
from stock.runner import load_strategy, run_strategy
from stock.signals import SizeType, buy, normalize_signals, sell


class BuyAndHoldStrategy(BaseStrategy):
    name = "buy_and_hold"

    def generate_signals(self, context: StrategyContext):
        return [buy(context.data.iloc[0]["date"]), sell(context.data.iloc[-1]["date"])]


class FakeStock:
    def __init__(self, stock_id: str) -> None:
        self.sid = stock_id
        self.date = [dt.date(2024, 1, 1), dt.date(2024, 1, 2), dt.date(2024, 1, 3)]
        self.open = [10.0, 11.0, 12.0]
        self.high = [11.0, 12.0, 13.0]
        self.low = [9.0, 10.0, 11.0]
        self.close = [10.0, 12.0, 14.0]
        self.price = [10.0, 12.0, 14.0]
        self.capacity = [100, 200, 300]
        self.turnover = [1000, 2000, 3000]
        self.change = [0.0, 2.0, 2.0]
        self.transaction = [1, 2, 3]
        self.fetch_31_called = False
        self.fetch_from_args: tuple[int, int] | None = None

    def fetch_31(self) -> None:
        self.fetch_31_called = True

    def fetch_from(self, year: int, month: int) -> None:
        self.fetch_from_args = (year, month)


def sample_data() -> pd.DataFrame:
    return normalize_price_data(
        pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
                "open": [10.0, 11.0, 12.0],
                "high": [11.0, 12.0, 13.0],
                "low": [9.0, 10.0, 11.0],
                "close": [10.0, 12.0, 14.0],
                "price": [10.0, 12.0, 14.0],
                "volume": [100, 200, 300],
                "turnover": [1000, 2000, 3000],
                "change": [0.0, 2.0, 2.0],
                "transaction": [1, 2, 3],
            }
        )
    )


def test_cached_stock_data_uses_cache_hit(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    cached = sample_data()
    cached.to_csv(cache_dir / "2330.csv", index=False)

    def fail_factory(stock_id: str):
        raise AssertionError("provider should not be called")

    result = get_stock_data_cached(
        "2330", cache_dir=cache_dir, stock_factory=fail_factory
    )

    assert result["close"].tolist() == [10.0, 12.0, 14.0]


def test_cached_stock_data_filters_requested_start_date(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    cached = pd.concat(
        [
            sample_data().assign(
                date=lambda data: data["date"] - pd.DateOffset(years=1)
            ),
            sample_data(),
        ]
    )
    cached.to_csv(cache_dir / "2330.csv", index=False)

    result = get_stock_data_cached(
        "2330",
        start_year=2024,
        start_month=1,
        cache_dir=cache_dir,
        stock_factory=lambda stock_id: (_ for _ in ()).throw(
            AssertionError("provider should not be called")
        ),
    )

    assert result["date"].min() == pd.Timestamp("2024-01-01")
    assert result["date"].max() == pd.Timestamp("2024-01-03")


def test_cached_stock_data_fetches_and_writes_cache(tmp_path):
    result = get_stock_data_cached("2330", cache_dir=tmp_path, stock_factory=FakeStock)

    assert result["volume"].tolist() == [100, 200, 300]
    assert (tmp_path / "2330.csv").exists()


def test_indicators_are_stable_for_known_data():
    values = pd.Series([10.0, 12.0, 14.0, 13.0])

    pd.testing.assert_series_equal(
        moving_average(values, 2),
        pd.Series([float("nan"), 11.0, 13.0, 13.5]),
    )
    assert returns(values).iloc[1] == pytest.approx(0.2)
    assert rsi(values, 2).iloc[-1] == pytest.approx(66.666666)


def test_signals_normalize_list_and_validate_dataframe():
    signals = normalize_signals(
        [
            buy(
                "2024-01-02",
                size_type=SizeType.CASH_PERCENT,
                size_value=0.5,
            ),
            sell("2024-01-03"),
        ]
    )

    assert signals["type"].tolist() == ["BUY", "SELL"]
    assert signals["size_type"].tolist() == ["CASH_PERCENT", "ALL"]
    assert signals["size_value"].iloc[0] == pytest.approx(0.5)
    with pytest.raises(ValueError, match="signal data missing columns"):
        normalize_signals(pd.DataFrame({"date": ["2024-01-01"]}))


def test_daily_backtest_buys_sells_and_summarizes():
    result = run_daily_backtest(
        sample_data(),
        normalize_signals([buy("2024-01-01"), sell("2024-01-03")]),
        stock_id="2330",
        strategy_name="sample",
        initial_cash=1000.0,
        commission_rate=0.0,
        tax_rate=0.0,
        execution_delay_days=0,
        execution_price="close",
    )

    assert result.trades["type"].tolist() == ["BUY", "SELL"]
    assert result.summary.loc[0, "final_equity"] == pytest.approx(1400.0)
    assert result.summary.loc[0, "total_return"] == pytest.approx(0.4)
    assert result.summary.loc[0, "win_rate"] == pytest.approx(1.0)


def test_daily_backtest_handles_no_signals():
    result = run_daily_backtest(
        sample_data(),
        normalize_signals([]),
        stock_id="2330",
        strategy_name="empty",
        initial_cash=1000.0,
        commission_rate=0.0,
        tax_rate=0.0,
        execution_delay_days=0,
        execution_price="close",
    )

    assert result.trades.empty
    assert result.summary.loc[0, "final_equity"] == pytest.approx(1000.0)


def test_daily_backtest_respects_signal_sizing():
    result = run_daily_backtest(
        sample_data(),
        normalize_signals(
            [
                buy(
                    "2024-01-01",
                    size_type=SizeType.CASH_PERCENT,
                    size_value=0.5,
                ),
                sell(
                    "2024-01-02",
                    size_type=SizeType.POSITION_PERCENT,
                    size_value=0.5,
                ),
            ]
        ),
        stock_id="2330",
        strategy_name="sample",
        initial_cash=1000.0,
        commission_rate=0.0,
        tax_rate=0.0,
        execution_delay_days=0,
        execution_price="close",
    )

    assert result.trades["type"].tolist() == ["BUY", "SELL"]
    assert result.trades["shares"].tolist() == [50, 25]
    assert result.equity_curve["shares"].tolist() == [50, 25, 25]
    assert result.summary.loc[0, "final_equity"] == pytest.approx(1150.0)


def test_daily_backtest_defaults_to_next_open_execution():
    result = run_daily_backtest(
        sample_data(),
        normalize_signals([buy("2024-01-01"), sell("2024-01-02")]),
        stock_id="2330",
        strategy_name="sample",
        initial_cash=1000.0,
        commission_rate=0.0,
        tax_rate=0.0,
    )

    assert result.trades["signal_date"].tolist() == [
        pd.Timestamp("2024-01-01"),
        pd.Timestamp("2024-01-02"),
    ]
    assert result.trades["date"].tolist() == [
        pd.Timestamp("2024-01-02"),
        pd.Timestamp("2024-01-03"),
    ]
    assert result.trades["price"].tolist() == [11.0, 12.0]
    assert result.summary.loc[0, "final_equity"] == pytest.approx(1090.0)
    assert result.summary.loc[0, "execution_delay_days"] == 1
    assert result.summary.loc[0, "execution_price"] == "open"


def test_daily_backtest_drops_signals_without_future_execution_date():
    result = run_daily_backtest(
        sample_data(),
        normalize_signals([buy("2024-01-03")]),
        stock_id="2330",
        strategy_name="sample",
        initial_cash=1000.0,
        commission_rate=0.0,
        tax_rate=0.0,
    )

    assert result.trades.empty
    assert result.summary.loc[0, "final_equity"] == pytest.approx(1000.0)


def test_daily_backtest_applies_costs_and_lot_size():
    result = run_daily_backtest(
        sample_data(),
        normalize_signals([buy("2024-01-01"), sell("2024-01-02")]),
        stock_id="2330",
        strategy_name="sample",
        initial_cash=1000.0,
        commission_rate=0.01,
        tax_rate=0.02,
        lot_size=10,
    )

    assert result.trades["shares"].tolist() == [90, 90]
    assert result.trades["fee"].tolist() == pytest.approx([9.9, 10.8])
    assert result.trades["tax"].tolist() == pytest.approx([0.0, 21.6])
    assert result.summary.loc[0, "final_equity"] == pytest.approx(1047.7)
    assert result.summary.loc[0, "lot_size"] == 10


def test_load_workspace_strategy():
    strategy_class = load_strategy("workspace.strategies:RsiReversalStrategy")

    assert issubclass(strategy_class, BaseStrategy)


def test_runner_executes_strategy_with_injected_data():
    strategy_path = f"{__name__}:BuyAndHoldStrategy"

    result = run_strategy(
        strategy_path,
        "2330",
        data=sample_data(),
        initial_cash=1000.0,
        commission_rate=0.0,
        tax_rate=0.0,
        execution_delay_days=0,
        execution_price="close",
    )

    assert result.signals["type"].tolist() == ["BUY", "SELL"]
    assert result.backtest.summary.loc[0, "strategy"] == "buy_and_hold"
