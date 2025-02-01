import pandas as pd

from src.events.events import EventLineStrategy


class RSILine(EventLineStrategy):
    events: pd.DataFrame
    ret: list[float]

    def analysis(self, data: pd.DataFrame) -> pd.DataFrame:
        self.events = data
        self.ret = []
        self.events["is_up"] = (data["close"] - data["open"]) > 0
        self.events["size"] = abs(data["close"] - data["open"])
        self.events["is_up"] = self.events["is_up"].astype(int)
        self.events["gain"] = self.events["size"] * self.events["is_up"]
        self.events["loss"] = self.events["size"] * (1 - self.events["is_up"])
        n = self.window_size
        self.events["avg_gain"] = (
            self.events["gain"].rolling(window=n, min_periods=n).mean()
        )
        self.events["avg_loss"] = (
            self.events["loss"].rolling(window=n, min_periods=n).mean()
        )
        # 計算相對強度 (RS)
        self.events["rs"] = self.events["avg_gain"] / self.events["avg_loss"]
        # 計算 RSI
        self.events["rsi"] = 100 - (100 / (1 + self.events["rs"]))

        return data

    def step(self, index, item):
        tmpRSI = item["rsi"]
        self.ret.append(tmpRSI)

    def result(self):
        return self.ret
