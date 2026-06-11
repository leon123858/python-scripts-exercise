from typing import Any

import pandas as pd

from stock.events.events import EventLineStrategy


class RSILine(EventLineStrategy):
    def __init__(self, window_size: int = 14) -> None:
        super().__init__(window_size=window_size)
        self.events = pd.DataFrame()
        self.ret: list[float] = []

    def analysis(self, data: pd.DataFrame) -> pd.DataFrame:
        self.events = data.copy()
        self.ret = []
        self.events["is_up"] = (self.events["close"] - self.events["open"]) > 0
        self.events["size"] = (self.events["close"] - self.events["open"]).abs()
        self.events["gain"] = self.events["size"] * self.events["is_up"].astype(int)
        self.events["loss"] = self.events["size"] * (~self.events["is_up"]).astype(int)
        self.events["avg_gain"] = (
            self.events["gain"]
            .rolling(window=self.window_size, min_periods=self.window_size)
            .mean()
        )
        self.events["avg_loss"] = (
            self.events["loss"]
            .rolling(window=self.window_size, min_periods=self.window_size)
            .mean()
        )
        self.events["rs"] = self.events["avg_gain"] / self.events["avg_loss"]
        self.events["rsi"] = 100 - (100 / (1 + self.events["rs"]))
        return self.events

    def step(self, index: Any, item: pd.Series) -> None:
        self.ret.append(item["rsi"])

    def result(self) -> list[float]:
        return self.ret
