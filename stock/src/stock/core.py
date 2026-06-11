from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class StrategyContext:
    stock_id: str
    data: pd.DataFrame
    params: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)
    prepared_data: pd.DataFrame | None = None


class BaseStrategy(ABC):
    name = "base_strategy"

    def prepare(self, context: StrategyContext) -> pd.DataFrame:
        return context.data

    @abstractmethod
    def generate_signals(self, context: StrategyContext) -> Any:
        raise NotImplementedError
