from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class EventStarStrategy(ABC):
    @abstractmethod
    def analysis(self, data: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError

    @abstractmethod
    def step(self, index: Any, item: pd.Series) -> None:
        raise NotImplementedError

    @abstractmethod
    def result(self) -> list[Any]:
        raise NotImplementedError


class EventLineStrategy(EventStarStrategy, ABC):
    def __init__(self, window_size: int = 14) -> None:
        self.window_size = window_size


def get_event_star(data: pd.DataFrame, strategy: EventStarStrategy) -> list[Any]:
    analyzed = strategy.analysis(data)
    for index, row in analyzed.iterrows():
        strategy.step(index, row)
    return strategy.result()


def get_event_line(
    data: pd.DataFrame, strategy: EventLineStrategy, window_size: int = 14
) -> list[Any]:
    strategy.window_size = window_size
    analyzed = strategy.analysis(data)
    for index, row in analyzed.iterrows():
        strategy.step(index, row)
    return strategy.result()
