import mplfinance as mpf
import pandas as pd


def draw_rsi_line(data: pd.DataFrame) -> None:
    apds = [mpf.make_addplot(data["rsi"], panel=1, title="RSI")]
    _, axes = mpf.plot(
        data,
        type="line",
        style="yahoo",
        addplot=apds,
        panel_ratios=(2, 1),
        returnfig=True,
    )
    axes[0].set_title("stock price")
    axes[1].set_title("RSI")
    mpf.show()
