import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd


def draw_rsi_line(data: pd.DataFrame):
    apds = [mpf.make_addplot(data["rsi"], panel=1, title="RSI")]
    fig, ax = mpf.plot(
        data,
        type="line",
        style="yahoo",
        addplot=apds,
        panel_ratios=(2, 1),
        returnfig=True,
    )
    ax[0].set_title("stock price")
    ax[1].set_title("RSI")
    mpf.show()
