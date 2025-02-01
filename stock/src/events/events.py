from abc import ABC, abstractmethod
import pandas as pd


class EventStarStrategy(ABC):
    @abstractmethod
    def analysis(self, data: pd.DataFrame):
        pass

    @abstractmethod
    def step(self, index, item):
        pass

    @abstractmethod
    def result(self):
        pass


class EventLineStrategy(EventStarStrategy, ABC):
    window_size = 14


def get_event_star(data: pd.DataFrame, strategy: EventStarStrategy):
    data = strategy.analysis(data)
    for index, row in data.iterrows():
        strategy.step(index, row)
    return strategy.result()


def get_event_line(data: pd.DataFrame, strategy: EventLineStrategy, window_size: int):
    data = strategy.analysis(data)
    strategy.window_size = window_size
    for index, row in data.iterrows():
        strategy.step(index, row)
    return strategy.result()
