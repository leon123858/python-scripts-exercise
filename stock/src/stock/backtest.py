from dataclasses import dataclass

import pandas as pd

from stock.signals import SignalType, SizeType, normalize_signals


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    equity_curve: pd.DataFrame
    summary: pd.DataFrame


def _clamp_ratio(value: float | None) -> float:
    if value is None or pd.isna(value):
        return 1.0
    return min(max(float(value), 0.0), 1.0)


def _positive_value(value: float | None) -> float:
    if value is None or pd.isna(value):
        return 0.0
    return max(float(value), 0.0)


def _buy_quantity(
    cash: float,
    price: float,
    size_type: SizeType,
    size_value: float | None,
    commission_rate: float,
) -> int:
    if cash <= 0:
        return 0

    if size_type == SizeType.CASH_PERCENT:
        budget = cash * _clamp_ratio(size_value)
    elif size_type == SizeType.CASH_AMOUNT:
        budget = min(cash, _positive_value(size_value))
    elif size_type == SizeType.SHARES:
        requested = int(_positive_value(size_value))
        affordable = int(cash // (price * (1 + commission_rate)))
        return min(requested, affordable)
    else:
        budget = cash

    return int(budget // (price * (1 + commission_rate)))


def _sell_quantity(
    shares: int,
    price: float,
    size_type: SizeType,
    size_value: float | None,
) -> int:
    if shares <= 0:
        return 0

    if size_type == SizeType.POSITION_PERCENT:
        return min(int(shares * _clamp_ratio(size_value)), shares)
    if size_type == SizeType.CASH_AMOUNT:
        target = _positive_value(size_value)
        return min(int(target // price), shares)
    if size_type == SizeType.SHARES:
        return min(int(_positive_value(size_value)), shares)
    return shares


def run_daily_backtest(
    data: pd.DataFrame,
    signals: pd.DataFrame,
    stock_id: str,
    strategy_name: str,
    initial_cash: float = 1_000_000.0,
    commission_rate: float = 0.0,
    tax_rate: float = 0.0,
) -> BacktestResult:
    normalized_signals = normalize_signals(signals)
    market = data.copy()
    market["date"] = pd.to_datetime(market["date"])
    market = market.sort_values("date").reset_index(drop=True)

    cash = initial_cash
    shares = 0
    entry_price = 0.0
    closed_returns: list[float] = []
    trades: list[dict[str, object]] = []
    equity_rows: list[dict[str, object]] = []

    signals_by_date = {
        date_value: group
        for date_value, group in normalized_signals.groupby(normalized_signals["date"])
    }

    for _, row in market.iterrows():
        current_date = pd.Timestamp(row["date"])
        price = float(row["close"])
        day_signals = signals_by_date.get(current_date)

        if day_signals is not None:
            for _, signal in day_signals.iterrows():
                signal_type = SignalType(signal["type"])
                size_type = SizeType(signal["size_type"])
                size_value = signal["size_value"]
                if signal_type == SignalType.BUY:
                    quantity = _buy_quantity(
                        cash, price, size_type, size_value, commission_rate
                    )
                    if quantity > 0:
                        gross = quantity * price
                        fee = gross * commission_rate
                        previous_position_cost = shares * entry_price
                        cash -= gross + fee
                        shares += quantity
                        entry_price = (previous_position_cost + gross + fee) / shares
                        trades.append(
                            {
                                "date": current_date,
                                "type": SignalType.BUY.value,
                                "price": price,
                                "shares": quantity,
                                "gross": gross,
                                "fee": fee,
                                "tax": 0.0,
                                "cash": cash,
                                "reason": signal["reason"],
                                "size_type": size_type.value,
                                "size_value": size_value,
                            }
                        )
                elif signal_type == SignalType.SELL and shares > 0:
                    quantity = _sell_quantity(shares, price, size_type, size_value)
                    if quantity <= 0:
                        continue
                    gross = quantity * price
                    fee = gross * commission_rate
                    tax = gross * tax_rate
                    cash += gross - fee - tax
                    closed_returns.append((price - entry_price) / entry_price)
                    trades.append(
                        {
                            "date": current_date,
                            "type": SignalType.SELL.value,
                            "price": price,
                            "shares": quantity,
                            "gross": gross,
                            "fee": fee,
                            "tax": tax,
                            "cash": cash,
                            "reason": signal["reason"],
                            "size_type": size_type.value,
                            "size_value": size_value,
                        }
                    )
                    shares -= quantity
                    if shares == 0:
                        entry_price = 0.0

        equity_rows.append(
            {
                "date": current_date,
                "cash": cash,
                "shares": shares,
                "close": price,
                "equity": cash + shares * price,
            }
        )

    equity_curve = pd.DataFrame(equity_rows)
    trades_df = pd.DataFrame(
        trades,
        columns=[
            "date",
            "type",
            "price",
            "shares",
            "gross",
            "fee",
            "tax",
            "cash",
            "reason",
            "size_type",
            "size_value",
        ],
    )
    final_equity = (
        float(equity_curve["equity"].iloc[-1])
        if not equity_curve.empty
        else initial_cash
    )
    sell_count = len(closed_returns)
    win_rate = (
        sum(1 for trade_return in closed_returns if trade_return > 0) / sell_count
        if sell_count
        else 0.0
    )
    summary = pd.DataFrame(
        [
            {
                "stock_id": stock_id,
                "strategy": strategy_name,
                "start_date": market["date"].iloc[0] if not market.empty else pd.NaT,
                "end_date": market["date"].iloc[-1] if not market.empty else pd.NaT,
                "initial_cash": initial_cash,
                "final_equity": final_equity,
                "total_return": (final_equity - initial_cash) / initial_cash,
                "trade_count": len(trades_df),
                "win_rate": win_rate,
            }
        ]
    )
    return BacktestResult(trades=trades_df, equity_curve=equity_curve, summary=summary)
