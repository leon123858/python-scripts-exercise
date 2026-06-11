from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Any

import pandas as pd


class SignalType(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class Signal:
    date: date | datetime | pd.Timestamp | str
    type: SignalType
    reason: str = ""
    metadata: dict[str, Any] | None = None


SIGNAL_COLUMNS = ["date", "type", "reason"]


def buy(
    signal_date: date | datetime | pd.Timestamp | str,
    reason: str = "",
    metadata: dict[str, Any] | None = None,
) -> Signal:
    return Signal(signal_date, SignalType.BUY, reason=reason, metadata=metadata)


def sell(
    signal_date: date | datetime | pd.Timestamp | str,
    reason: str = "",
    metadata: dict[str, Any] | None = None,
) -> Signal:
    return Signal(signal_date, SignalType.SELL, reason=reason, metadata=metadata)


def normalize_signals(signals: list[Signal] | pd.DataFrame) -> pd.DataFrame:
    if isinstance(signals, pd.DataFrame):
        missing = set(SIGNAL_COLUMNS) - set(signals.columns)
        if missing:
            raise ValueError(f"signal data missing columns: {sorted(missing)}")
        normalized = signals.copy()
    else:
        normalized = pd.DataFrame(
            {
                "date": [signal.date for signal in signals],
                "type": [signal.type.value for signal in signals],
                "reason": [signal.reason for signal in signals],
            }
        )

    if normalized.empty:
        return pd.DataFrame(columns=SIGNAL_COLUMNS)

    normalized["date"] = pd.to_datetime(normalized["date"])
    normalized["type"] = normalized["type"].map(lambda value: SignalType(value).value)
    return normalized.sort_values("date").reset_index(drop=True)
