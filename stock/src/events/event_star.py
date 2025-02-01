from datetime import datetime

import pandas as pd

from src.events.events import EventStarStrategy


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
                self.eventQueue[0]["is_down"] is True
                and self.eventQueue[1]["is_down"] is True
                and self.eventQueue[2]["is_down"] is True
            ):
                if (
                    self.eventQueue[0]["K_size"]
                    < self.eventQueue[1]["K_size"]
                    < self.eventQueue[2]["K_size"]
                ):
                    self.events.append(index)
            self.eventQueue = self.eventQueue[1:]

    def result(self):
        return self.events


class Red3(EventStarStrategy):
    events: list[datetime] = []
    eventQueue: list[object] = []

    def analysis(self, data: pd.DataFrame) -> pd.DataFrame:
        data["K_size"] = abs(data["close"] - data["open"])
        data["is_up"] = data["close"] > data["open"]
        return data

    def step(self, index, item):
        self.eventQueue.append(item)
        if len(self.eventQueue) == 3:
            if (
                self.eventQueue[0]["is_up"] is True
                and self.eventQueue[1]["is_up"] is True
                and self.eventQueue[2]["is_up"] is True
            ):
                if (
                    self.eventQueue[0]["K_size"]
                    < self.eventQueue[1]["K_size"]
                    < self.eventQueue[2]["K_size"]
                ):
                    self.events.append(index)
            self.eventQueue = self.eventQueue[1:]

    def result(self):
        return self.events
