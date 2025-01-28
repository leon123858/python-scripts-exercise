from datetime import datetime

import pandas as pd
from abc import ABC, abstractmethod


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


class EveningStar(EventStarStrategy):
    events: list[datetime] = []
    eventQueue: list[object] = []

    def analysis(self, data: pd.DataFrame) -> pd.DataFrame:
        data["K_size"] = abs(data["close"] - data["open"])
        mean_k_size = data["K_size"].mean()
        std_k_size = data["K_size"].std()
        threshold = mean_k_size + std_k_size
        data["big_k"] = data["K_size"] > threshold
        data["is_up"] = data["close"] > data["open"]
        return data

    def step(self, index, item):
        self.eventQueue.append(item)
        if len(self.eventQueue) == 3:
            if (
                self.eventQueue[0]["big_k"] is True
                and self.eventQueue[0]["is_up"] is False
            ):
                if self.eventQueue[1]["big_k"] is False:
                    if (
                        self.eventQueue[2]["big_k"] is True
                        and self.eventQueue[2]["is_up"] is True
                    ):
                        self.events.append(index)
            self.eventQueue = self.eventQueue[1:]

    def result(self):
        return self.events


class MorningStar(EventStarStrategy):
    events: list[datetime] = []
    eventQueue: list[object] = []

    def analysis(self, data: pd.DataFrame) -> pd.DataFrame:
        data["K_size"] = abs(data["close"] - data["open"])
        mean_k_size = data["K_size"].mean()
        std_k_size = data["K_size"].std()
        threshold = mean_k_size + std_k_size
        data["big_k"] = data["K_size"] > threshold
        data["is_up"] = data["close"] > data["open"]
        return data

    def step(self, index, item):
        self.eventQueue.append(item)
        if len(self.eventQueue) == 3:
            if (
                self.eventQueue[0]["big_k"] is True
                and self.eventQueue[0]["is_up"] is True
            ):
                if self.eventQueue[1]["big_k"] is False:
                    if (
                        self.eventQueue[2]["big_k"] is True
                        and self.eventQueue[2]["is_up"] is False
                    ):
                        self.events.append(index)
            self.eventQueue = self.eventQueue[1:]

    def result(self):
        return self.events

class Black3(EventStarStrategy):
    events: list[datetime] = []
    eventQueue: list[object] = []

    def analysis(self, data: pd.DataFrame) -> pd.DataFrame:
        data["K_size"] = abs(data["close"] - data["open"])
        data["is_down"] = data["close"] < data["open"]
        return data

    def step(self, index, item):
        self.eventQueue.append(item)
        if len(self.eventQueue) == 3:
            if (
                    self.eventQueue[0]["is_down"] is True and self.eventQueue[1]["is_down"] is True and self.eventQueue[2]["is_down"] is True
            ):
                if self.eventQueue[0]["K_size"] < self.eventQueue[1]["K_size"] < self.eventQueue[2]["K_size"]:
                        self.events.append(index)
            self.eventQueue = self.eventQueue[1:]

    def result(self):
        return self.events

def get_event_star(data: pd.DataFrame, strategy: EventStarStrategy):
    data.index = data["date"]
    data = strategy.analysis(data)
    for index, row in data.iterrows():
        strategy.step(index, row)
    return strategy.result()
