from collections.abc import Sequence
from typing import Any

import pandas as pd


def create_dataframe_from_lists(
    *args: Sequence[Any], columns: Sequence[str] | None = None
) -> pd.DataFrame:
    """Create a DataFrame from equally sized sequences."""
    lengths = [len(values) for values in args]
    if len(set(lengths)) != 1:
        raise ValueError("all list len should same")

    if columns is None:
        raise ValueError("should have col name")

    if len(columns) != len(args):
        raise ValueError("col name len not right")

    return pd.DataFrame(dict(zip(columns, args)))
