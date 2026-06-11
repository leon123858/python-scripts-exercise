import pandas as pd


def moving_average(values: pd.Series, window: int) -> pd.Series:
    return values.rolling(window=window, min_periods=window).mean()


def returns(values: pd.Series, periods: int = 1) -> pd.Series:
    return values.pct_change(periods=periods)


def rsi(values: pd.Series, window: int = 14) -> pd.Series:
    delta = values.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()
    relative_strength = avg_gain / avg_loss
    return 100 - (100 / (1 + relative_strength))
