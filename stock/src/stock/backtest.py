from dataclasses import dataclass

import pandas as pd

from stock.signals import SignalType, normalize_signals


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    equity_curve: pd.DataFrame
    summary: pd.DataFrame


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
                if signal_type == SignalType.BUY and shares == 0 and cash > 0:
                    quantity = int(cash // price)
                    if quantity > 0:
                        gross = quantity * price
                        fee = gross * commission_rate
                        cash -= gross + fee
                        shares += quantity
                        entry_price = price
                        trades.append(
                            {
                                "date": current_date,
                                "type": SignalType.BUY.value,
                                "price": price,
                                "shares": quantity,
                                "cash": cash,
                                "reason": signal["reason"],
                            }
                        )
                elif signal_type == SignalType.SELL and shares > 0:
                    gross = shares * price
                    fee = gross * commission_rate
                    tax = gross * tax_rate
                    cash += gross - fee - tax
                    closed_returns.append((price - entry_price) / entry_price)
                    trades.append(
                        {
                            "date": current_date,
                            "type": SignalType.SELL.value,
                            "price": price,
                            "shares": shares,
                            "cash": cash,
                            "reason": signal["reason"],
                        }
                    )
                    shares = 0
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
        trades, columns=["date", "type", "price", "shares", "cash", "reason"]
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
