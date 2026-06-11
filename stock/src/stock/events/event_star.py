from typing import Any

import pandas as pd

from stock.events.events import EventStarStrategy


class _ThreeCandleStrategy(EventStarStrategy):
    def __init__(self) -> None:
        self.events: list[Any] = []
        self.event_queue: list[pd.Series] = []

    def result(self) -> list[Any]:
        return self.events

    def _append_and_trim(self, item: pd.Series) -> bool:
        self.event_queue.append(item)
        if len(self.event_queue) < 3:
            return False
        if len(self.event_queue) > 3:
            self.event_queue = self.event_queue[-3:]
        return True

    def _advance(self) -> None:
        self.event_queue = self.event_queue[1:]


class EveningStar(_ThreeCandleStrategy):
    def analysis(self, data: pd.DataFrame) -> pd.DataFrame:
        analyzed = data.copy()
        analyzed["K_size"] = (analyzed["close"] - analyzed["open"]).abs()
        threshold = analyzed["K_size"].mean() + analyzed["K_size"].std()
        analyzed["big_k"] = analyzed["K_size"] > threshold
        analyzed["is_up"] = analyzed["close"] > analyzed["open"]
        return analyzed

    def step(self, index: Any, item: pd.Series) -> None:
        if not self._append_and_trim(item):
            return
        first, second, third = self.event_queue
        if (
            bool(first["big_k"])
            and not bool(first["is_up"])
            and not bool(second["big_k"])
            and bool(third["big_k"])
            and bool(third["is_up"])
        ):
            self.events.append(index)
        self._advance()


class MorningStar(_ThreeCandleStrategy):
    def analysis(self, data: pd.DataFrame) -> pd.DataFrame:
        analyzed = data.copy()
        analyzed["K_size"] = (analyzed["close"] - analyzed["open"]).abs()
        threshold = analyzed["K_size"].mean() + analyzed["K_size"].std()
        analyzed["big_k"] = analyzed["K_size"] > threshold
        analyzed["is_up"] = analyzed["close"] > analyzed["open"]
        return analyzed

    def step(self, index: Any, item: pd.Series) -> None:
        if not self._append_and_trim(item):
            return
        first, second, third = self.event_queue
        if (
            bool(first["big_k"])
            and bool(first["is_up"])
            and not bool(second["big_k"])
            and bool(third["big_k"])
            and not bool(third["is_up"])
        ):
            self.events.append(index)
        self._advance()


class Black3(_ThreeCandleStrategy):
    def analysis(self, data: pd.DataFrame) -> pd.DataFrame:
        analyzed = data.copy()
        analyzed["K_size"] = (analyzed["close"] - analyzed["open"]).abs()
        analyzed["is_down"] = analyzed["close"] < analyzed["open"]
        return analyzed

    def step(self, index: Any, item: pd.Series) -> None:
        if not self._append_and_trim(item):
            return
        first, second, third = self.event_queue
        if (
            bool(first["is_down"])
            and bool(second["is_down"])
            and bool(third["is_down"])
            and first["K_size"] < second["K_size"] < third["K_size"]
        ):
            self.events.append(index)
        self._advance()


class Red3(_ThreeCandleStrategy):
    def analysis(self, data: pd.DataFrame) -> pd.DataFrame:
        analyzed = data.copy()
        analyzed["K_size"] = (analyzed["close"] - analyzed["open"]).abs()
        analyzed["is_up"] = analyzed["close"] > analyzed["open"]
        return analyzed

    def step(self, index: Any, item: pd.Series) -> None:
        if not self._append_and_trim(item):
            return
        first, second, third = self.event_queue
        if (
            bool(first["is_up"])
            and bool(second["is_up"])
            and bool(third["is_up"])
            and first["K_size"] < second["K_size"] < third["K_size"]
        ):
            self.events.append(index)
        self._advance()
