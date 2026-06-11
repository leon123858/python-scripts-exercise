import pandas as pd
import pytest

from stock.core import StrategyContext
from stock.runner import run_strategy
from workspace.strategies import ThreeSoldiersStrategy


def three_soldiers_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2024-01-01",
                    "2024-01-02",
                    "2024-01-03",
                    "2024-01-04",
                    "2024-01-05",
                    "2024-01-06",
                ]
            ),
            "open": [10.0, 11.0, 12.0, 14.5, 13.5, 12.5],
            "high": [12.5, 13.4, 14.2, 14.7, 13.7, 12.7],
            "low": [9.8, 10.8, 11.8, 12.8, 11.8, 10.8],
            "close": [12.0, 13.0, 14.0, 13.0, 12.0, 11.0],
        }
    )


def test_three_soldiers_strategy_generates_buy_and_sell_signals():
    data = three_soldiers_data()
    context = StrategyContext(stock_id="2330", data=data)
    strategy = ThreeSoldiersStrategy()

    context.prepared_data = strategy.prepare(context)
    signals = strategy.generate_signals(context)

    assert [signal.type.value for signal in signals] == ["BUY", "SELL"]
    assert signals[0].size_type.value == "CASH_PERCENT"
    assert signals[0].size_value == pytest.approx(0.4166666666666667)
    assert signals[1].size_type.value == "ALL"
    assert [signal.date for signal in signals] == [
        pd.Timestamp("2024-01-03"),
        pd.Timestamp("2024-01-05"),
    ]
    assert context.prepared_data["red_three_soldiers"].tolist() == [
        False,
        False,
        True,
        False,
        False,
        False,
    ]
    assert context.prepared_data["black_three_soldiers"].tolist() == [
        False,
        False,
        False,
        False,
        True,
        False,
    ]


def test_three_soldiers_strategy_runs_through_backtest():
    result = run_strategy(
        "workspace.strategies:ThreeSoldiersStrategy",
        "2330",
        data=three_soldiers_data(),
        initial_cash=1000.0,
    )

    assert result.signals["type"].tolist() == ["BUY", "SELL"]
    assert result.signals["size_type"].tolist() == ["CASH_PERCENT", "ALL"]
    assert result.backtest.summary.loc[0, "strategy"] == "three_soldiers"
    assert result.backtest.trades["price"].tolist() == [14.0, 12.0]
    assert result.backtest.trades["shares"].tolist() == [29, 29]


def test_three_soldiers_pattern_resets_after_trigger():
    data = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2024-01-01",
                    "2024-01-02",
                    "2024-01-03",
                    "2024-01-04",
                    "2024-01-05",
                ]
            ),
            "open": [10.0, 11.0, 12.0, 13.0, 14.0],
            "high": [10.5, 11.5, 12.5, 13.5, 14.5],
            "low": [9.5, 10.5, 11.5, 12.5, 13.5],
            "close": [10.0, 11.0, 12.0, 13.0, 14.0],
        }
    )
    context = StrategyContext(stock_id="2330", data=data)
    strategy = ThreeSoldiersStrategy()

    prepared = strategy.prepare(context)

    assert prepared["red_three_soldiers"].tolist() == [
        False,
        False,
        True,
        False,
        True,
    ]
