import importlib
from dataclasses import dataclass
from typing import Any

import pandas as pd

from stock.backtest import BacktestResult, run_daily_backtest
from stock.core import BaseStrategy, StrategyContext
from stock.data import get_stock_data_cached
from stock.signals import normalize_signals


@dataclass
class AnalysisResult:
    context: StrategyContext
    signals: pd.DataFrame
    backtest: BacktestResult


def load_strategy(strategy_path: str) -> type[BaseStrategy]:
    if ":" not in strategy_path:
        raise ValueError("strategy should use 'module:ClassName' format")
    module_name, class_name = strategy_path.split(":", 1)
    module = importlib.import_module(module_name)
    strategy_class = getattr(module, class_name)
    if not issubclass(strategy_class, BaseStrategy):
        raise TypeError(f"{strategy_path} should inherit from BaseStrategy")
    return strategy_class


def run_strategy(
    strategy_path: str,
    stock_id: str,
    start_year: int | None = None,
    start_month: int | None = None,
    params: dict[str, object] | None = None,
    initial_cash: float = 1_000_000.0,
    commission_rate: float = 0.0,
    tax_rate: float = 0.0,
    data: pd.DataFrame | None = None,
    data_kwargs: dict[str, Any] | None = None,
) -> AnalysisResult:
    strategy_class = load_strategy(strategy_path)
    strategy = strategy_class()
    market_data = data
    if market_data is None:
        market_data = get_stock_data_cached(
            stock_id,
            start_year=start_year,
            start_month=start_month,
            **(data_kwargs or {}),
        )
    context = StrategyContext(
        stock_id=stock_id,
        data=market_data,
        params=params or {},
        metadata={"strategy_path": strategy_path},
    )
    context.prepared_data = strategy.prepare(context)
    signals = normalize_signals(strategy.generate_signals(context))
    backtest = run_daily_backtest(
        context.prepared_data,
        signals,
        stock_id=stock_id,
        strategy_name=strategy.name,
        initial_cash=initial_cash,
        commission_rate=commission_rate,
        tax_rate=tax_rate,
    )
    return AnalysisResult(context=context, signals=signals, backtest=backtest)
