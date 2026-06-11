from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Any

import pandas as pd


class SignalType(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class SizeType(StrEnum):
    ALL = "ALL"
    CASH_AMOUNT = "CASH_AMOUNT"
    CASH_PERCENT = "CASH_PERCENT"
    SHARES = "SHARES"
    POSITION_PERCENT = "POSITION_PERCENT"


@dataclass(frozen=True)
class Signal:
    date: date | datetime | pd.Timestamp | str
    type: SignalType
    reason: str = ""
    size_type: SizeType = SizeType.ALL
    size_value: float | None = None
    metadata: dict[str, Any] | None = None


SIGNAL_COLUMNS = ["date", "type", "reason", "size_type", "size_value"]


def buy(
    signal_date: date | datetime | pd.Timestamp | str,
    reason: str = "",
    size_type: SizeType | str = SizeType.ALL,
    size_value: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> Signal:
    return Signal(
        signal_date,
        SignalType.BUY,
        reason=reason,
        size_type=SizeType(size_type),
        size_value=size_value,
        metadata=metadata,
    )


def sell(
    signal_date: date | datetime | pd.Timestamp | str,
    reason: str = "",
    size_type: SizeType | str = SizeType.ALL,
    size_value: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> Signal:
    return Signal(
        signal_date,
        SignalType.SELL,
        reason=reason,
        size_type=SizeType(size_type),
        size_value=size_value,
        metadata=metadata,
    )


def normalize_signals(signals: list[Signal] | pd.DataFrame) -> pd.DataFrame:
    if isinstance(signals, pd.DataFrame):
        required_columns = {"date", "type", "reason"}
        missing = required_columns - set(signals.columns)
        if missing:
            raise ValueError(f"signal data missing columns: {sorted(missing)}")
        normalized = signals.copy()
        if "size_type" not in normalized.columns:
            normalized["size_type"] = SizeType.ALL.value
        if "size_value" not in normalized.columns:
            normalized["size_value"] = None
    else:
        normalized = pd.DataFrame(
            {
                "date": [signal.date for signal in signals],
                "type": [signal.type.value for signal in signals],
                "reason": [signal.reason for signal in signals],
                "size_type": [signal.size_type.value for signal in signals],
                "size_value": [signal.size_value for signal in signals],
            }
        )

    if normalized.empty:
        return pd.DataFrame(columns=SIGNAL_COLUMNS)

    normalized["date"] = pd.to_datetime(normalized["date"])
    normalized["type"] = normalized["type"].map(lambda value: SignalType(value).value)
    normalized["size_type"] = normalized["size_type"].map(
        lambda value: SizeType(value).value
    )
    normalized["size_value"] = pd.to_numeric(normalized["size_value"], errors="coerce")
    return normalized.sort_values("date").reset_index(drop=True)
