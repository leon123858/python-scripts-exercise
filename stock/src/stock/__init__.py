"""Taiwan stock analysis framework."""

from stock.core import BaseStrategy, StrategyContext
from stock.runner import AnalysisResult, run_strategy
from stock.signals import Signal, SignalType, buy, sell

__version__ = "0.1.0"

__all__ = [
    "AnalysisResult",
    "BaseStrategy",
    "Signal",
    "SignalType",
    "StrategyContext",
    "__version__",
    "buy",
    "run_strategy",
    "sell",
]
