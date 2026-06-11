from stock import BaseStrategy
from stock.indicators import moving_average, returns, rsi
from stock.signals import buy, sell


class RsiReversalStrategy(BaseStrategy):
    name = "rsi_reversal"

    def prepare(self, context):
        data = context.data.copy()
        data["rsi"] = rsi(data["close"], window=14)
        return data

    def generate_signals(self, context):
        data = context.prepared_data
        if data is None:
            return []
        signals = []
        for row in data.itertuples(index=False):
            if row.rsi < 30:
                signals.append(buy(row.date, reason="rsi below 30"))
            elif row.rsi > 70:
                signals.append(sell(row.date, reason="rsi above 70"))
        return signals


class TaiwanOperationStrategy(BaseStrategy):
    name = "taiwan_operation"

    def prepare(self, context):
        data = context.data.copy()
        data["ma20"] = moving_average(data["close"], window=20)
        data["ma60"] = moving_average(data["close"], window=60)
        data["rsi14"] = rsi(data["close"], window=14)
        data["return_20d"] = returns(data["close"], periods=20)
        return data

    def generate_signals(self, context):
        data = context.prepared_data
        if data is None:
            return []

        signals = []
        holding = False
        for row in data.itertuples(index=False):
            if row.ma20 != row.ma20 or row.ma60 != row.ma60 or row.rsi14 != row.rsi14:
                continue

            trend_up = row.close > row.ma20 > row.ma60
            momentum_ok = row.rsi14 >= 50
            risk_off = row.close < row.ma20 or row.rsi14 < 45

            if not holding and trend_up and momentum_ok:
                signals.append(
                    buy(row.date, reason="close > ma20 > ma60 and rsi14 >= 50")
                )
                holding = True
            elif holding and risk_off:
                signals.append(sell(row.date, reason="close < ma20 or rsi14 < 45"))
                holding = False

        return signals
