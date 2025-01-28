import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd


def draw_k_line(data: pd.DataFrame):
    required_columns = ["Open", "High", "Low", "Close", "Volume"]
    if not set(required_columns).issubset(data.columns):
        missing_columns = set(required_columns) - set(data.columns)
        print(f"缺少以下欄位: {missing_columns}")
        raise ValueError("miss table col")
    # 繪製 K 線圖
    mpf.plot(data, type="candle", style="yahoo", volume=True)
    plt.show()


def convert2k_line_diagram(data: pd.DataFrame) -> pd.DataFrame:
    new_data = data[["date", "open", "low", "high", "close", "turnover"]]
    new_df = new_data.rename(
        columns={
            "open": "Open",
            "low": "Low",
            "high": "High",
            "close": "Close",
            "turnover": "Volume",
        }
    )
    new_df.index = data["date"]
    return new_df
