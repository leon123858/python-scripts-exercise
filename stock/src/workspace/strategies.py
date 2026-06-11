from stock import BaseStrategy
from stock.indicators import moving_average, returns, rsi
from stock.signals import SizeType, buy, sell


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


class MaTrendStrategy(BaseStrategy):
    name = "ma_trend"

    def prepare(self, context):
        data = context.data.copy()
        window = int(context.params.get("window", 20))
        data["ma"] = moving_average(data["close"], window=window)
        return data

    def generate_signals(self, context):
        data = context.prepared_data
        if data is None:
            return []

        signals = []
        holding = False
        previous_close_above_ma = None
        for row in data.itertuples(index=False):
            if row.ma != row.ma:
                continue

            close_above_ma = row.close > row.ma
            if previous_close_above_ma is None:
                previous_close_above_ma = close_above_ma
                continue

            if not holding and close_above_ma and not previous_close_above_ma:
                signals.append(
                    buy(row.date, reason="close crossed above moving average")
                )
                holding = True
            elif holding and not close_above_ma and previous_close_above_ma:
                signals.append(
                    sell(row.date, reason="close crossed below moving average")
                )
                holding = False

            previous_close_above_ma = close_above_ma

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


class ThreeSoldiersStrategy(BaseStrategy):
    name = "three_soldiers"

    def prepare(self, context):
        data = context.data.copy()
        min_run_days = int(context.params.get("min_run_days", 3))
        trigger_ratio = float(context.params.get("trigger_ratio", 0.5))

        data["red_three_soldiers"] = False
        data["black_three_soldiers"] = False
        data["red_three_soldiers_strength"] = 0.0

        if len(data) < min_run_days:
            return data

        close_values = data["close"].astype(float).tolist()
        current_direction = 0
        run_start_index = 0
        run_length = 1
        first_leg_ratio = 0.0

        for index in range(1, len(data)):
            previous_close = close_values[index - 1]
            current_close = close_values[index]
            if current_close == previous_close:
                current_direction = 0
                run_start_index = index
                run_length = 1
                first_leg_ratio = 0.0
                continue

            direction = 1 if current_close > previous_close else -1
            if direction != current_direction:
                current_direction = direction
                run_start_index = index - 1
                run_length = 2
                first_leg_ratio = abs(current_close - previous_close) / previous_close
            else:
                run_length += 1

            start_close = close_values[run_start_index]
            cumulative_ratio = abs(current_close - start_close) / start_close
            is_triggered = (
                run_length >= min_run_days
                and first_leg_ratio > 0
                and cumulative_ratio >= first_leg_ratio * trigger_ratio
            )
            if not is_triggered:
                continue

            if direction > 0:
                data.at[data.index[index], "red_three_soldiers"] = True
                data.at[data.index[index], "red_three_soldiers_strength"] = min(
                    cumulative_ratio,
                    1.0,
                )
            else:
                data.at[data.index[index], "black_three_soldiers"] = True

            current_direction = 0
            run_start_index = index
            run_length = 1
            first_leg_ratio = 0.0
        return data

    def generate_signals(self, context):
        data = context.prepared_data
        if data is None:
            return []

        signals = []
        holding = False
        base_cash_percent = float(context.params.get("base_cash_percent", 0.35))
        max_cash_percent = float(context.params.get("max_cash_percent", 0.75))
        for row in data.itertuples(index=False):
            if row.red_three_soldiers and not holding:
                strength = max(float(row.red_three_soldiers_strength), 0.0)
                cash_percent = min(
                    base_cash_percent
                    + strength * (max_cash_percent - base_cash_percent),
                    max_cash_percent,
                )
                signals.append(
                    buy(
                        row.date,
                        reason="red three soldiers",
                        size_type=SizeType.CASH_PERCENT,
                        size_value=cash_percent,
                    )
                )
                holding = True
            elif row.black_three_soldiers and holding:
                signals.append(
                    sell(
                        row.date,
                        reason="black three soldiers",
                        size_type=SizeType.ALL,
                    )
                )
                holding = False
        return signals
