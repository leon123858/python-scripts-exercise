import pandas as pd
import pytest

from stock.diagram.k_line import convert_to_k_line_diagram, draw_k_line


def test_convert_to_k_line_diagram():
    data = pd.DataFrame(
        {
            "date": pd.to_datetime(["2023-01-01", "2023-01-02"]),
            "open": [10.0, 11.0],
            "low": [9.0, 10.0],
            "high": [12.0, 13.0],
            "close": [11.0, 12.0],
            "turnover": [1000, 2000],
        }
    )

    result = convert_to_k_line_diagram(data)

    assert list(result.columns) == ["date", "Open", "Low", "High", "Close", "Volume"]
    assert list(result.index) == list(data["date"])
    assert result["Volume"].tolist() == [1000, 2000]


def test_draw_k_line_requires_ohlcv_columns():
    with pytest.raises(ValueError, match="miss table col"):
        draw_k_line(pd.DataFrame({"Open": [10.0]}))
