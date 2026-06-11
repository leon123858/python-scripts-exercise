from dataclasses import dataclass
from typing import Literal

import pandas as pd

from stock.signals import SignalType, SizeType, normalize_signals

ExecutionPrice = Literal["open", "high", "low", "close", "price"]


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
    lot_size: int,
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
        quantity = min(requested, affordable)
        return quantity - quantity % lot_size
    else:
        budget = cash

    quantity = int(budget // (price * (1 + commission_rate)))
    return quantity - quantity % lot_size


def _sell_quantity(
    shares: int,
    price: float,
    size_type: SizeType,
    size_value: float | None,
    lot_size: int,
) -> int:
    if shares <= 0:
        return 0

    if size_type == SizeType.POSITION_PERCENT:
        quantity = min(int(shares * _clamp_ratio(size_value)), shares)
    elif size_type == SizeType.CASH_AMOUNT:
        target = _positive_value(size_value)
        quantity = min(int(target // price), shares)
    elif size_type == SizeType.SHARES:
        quantity = min(int(_positive_value(size_value)), shares)
    else:
        quantity = shares

    if quantity == shares:
        return quantity
    return quantity - quantity % lot_size


def _scheduled_signals(
    market_dates: pd.Series,
    signals: pd.DataFrame,
    execution_delay_days: int,
) -> dict[pd.Timestamp, list[pd.Series]]:
    if execution_delay_days < 0:
        raise ValueError("execution_delay_days should be greater than or equal to 0")

    scheduled: dict[pd.Timestamp, list[pd.Series]] = {}
    if signals.empty:
        return scheduled

    dates = pd.to_datetime(market_dates).reset_index(drop=True)
    for _, signal in signals.iterrows():
        signal_date = pd.Timestamp(signal["date"])
        candidates = dates[dates >= signal_date]
        if candidates.empty:
            continue
        signal_index = int(candidates.index[0]) + execution_delay_days
        if signal_index >= len(dates):
            continue
        execution_date = pd.Timestamp(dates.iloc[signal_index])
        scheduled.setdefault(execution_date, []).append(signal)
    return scheduled


def run_daily_backtest(
    data: pd.DataFrame,
    signals: pd.DataFrame,
    stock_id: str,
    strategy_name: str,
    initial_cash: float = 1_000_000.0,
    commission_rate: float = 0.001425,
    tax_rate: float = 0.003,
    execution_delay_days: int = 1,
    execution_price: ExecutionPrice = "open",
    lot_size: int = 1,
) -> BacktestResult:
    if lot_size < 1:
        raise ValueError("lot_size should be greater than or equal to 1")

    normalized_signals = normalize_signals(signals)
    market = data.copy()
    market["date"] = pd.to_datetime(market["date"])
    market = market.sort_values("date").reset_index(drop=True)
    if execution_price not in market.columns:
        raise ValueError(f"execution_price column not found: {execution_price}")

    cash = initial_cash
    shares = 0
    entry_price = 0.0
    closed_returns: list[float] = []
    trades: list[dict[str, object]] = []
    equity_rows: list[dict[str, object]] = []

    signals_by_date = _scheduled_signals(
        market["date"],
        normalized_signals,
        execution_delay_days,
    )

    for _, row in market.iterrows():
        current_date = pd.Timestamp(row["date"])
        mark_price = float(row["close"])
        execution_price_value = float(row[execution_price])
        day_signals = signals_by_date.get(current_date)

        if day_signals is not None:
            for signal in day_signals:
                signal_type = SignalType(signal["type"])
                size_type = SizeType(signal["size_type"])
                size_value = signal["size_value"]
                if signal_type == SignalType.BUY:
                    quantity = _buy_quantity(
                        cash,
                        execution_price_value,
                        size_type,
                        size_value,
                        commission_rate,
                        lot_size,
                    )
                    if quantity > 0:
                        gross = quantity * execution_price_value
                        fee = gross * commission_rate
                        previous_position_cost = shares * entry_price
                        cash -= gross + fee
                        shares += quantity
                        entry_price = (previous_position_cost + gross + fee) / shares
                        trades.append(
                            {
                                "date": current_date,
                                "signal_date": signal["date"],
                                "type": SignalType.BUY.value,
                                "price": execution_price_value,
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
                    quantity = _sell_quantity(
                        shares,
                        execution_price_value,
                        size_type,
                        size_value,
                        lot_size,
                    )
                    if quantity <= 0:
                        continue
                    gross = quantity * execution_price_value
                    fee = gross * commission_rate
                    tax = gross * tax_rate
                    cash += gross - fee - tax
                    closed_returns.append(
                        (execution_price_value - entry_price) / entry_price
                    )
                    trades.append(
                        {
                            "date": current_date,
                            "signal_date": signal["date"],
                            "type": SignalType.SELL.value,
                            "price": execution_price_value,
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
                "close": mark_price,
                "equity": cash + shares * mark_price,
            }
        )

    equity_curve = pd.DataFrame(equity_rows)
    trades_df = pd.DataFrame(
        trades,
        columns=[
            "date",
            "signal_date",
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
                "commission_rate": commission_rate,
                "tax_rate": tax_rate,
                "execution_delay_days": execution_delay_days,
                "execution_price": execution_price,
                "lot_size": lot_size,
            }
        ]
    )
    return BacktestResult(trades=trades_df, equity_curve=equity_curve, summary=summary)
