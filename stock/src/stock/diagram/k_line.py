import mplfinance as mpf
import pandas as pd

K_LINE_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def draw_k_line(data: pd.DataFrame) -> None:
    missing_columns = set(K_LINE_COLUMNS) - set(data.columns)
    if missing_columns:
        raise ValueError(f"miss table col: {sorted(missing_columns)}")
    mpf.plot(data, type="candle", style="yahoo", volume=True)
    mpf.show()


def convert_to_k_line_diagram(data: pd.DataFrame) -> pd.DataFrame:
    new_df = data[["date", "open", "low", "high", "close", "turnover"]].rename(
        columns={
            "open": "Open",
            "low": "Low",
            "high": "High",
            "close": "Close",
            "turnover": "Volume",
        }
    )
    new_df.index = pd.Index(data["date"])
    return new_df
