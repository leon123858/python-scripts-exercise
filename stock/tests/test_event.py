import numpy as np
import pandas as pd
import pytest
from pandas import Timestamp

from stock.events.event_star import Black3, EveningStar, Red3
from stock.events.events import get_event_line, get_event_star
from stock.events.lines import RSILine
from stock.utils.revenue import get_revenue_by_date_offset, get_revenue_by_line_offset


def test_evening_star_analysis():
    data = pd.DataFrame(
        {
            "date": pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]),
            "open": [10, 12, 9],
            "close": [8, 11, 15],
        }
    )

    analyzed_data = EveningStar().analysis(data)

    expected_big_k = pd.Series([False, False, True], name="big_k")
    expected_is_up = pd.Series([False, False, True], name="is_up")
    pd.testing.assert_series_equal(analyzed_data["big_k"], expected_big_k)
    pd.testing.assert_series_equal(analyzed_data["is_up"], expected_is_up)
    assert "big_k" not in data.columns


def test_catch_event():
    data = pd.DataFrame(
        {
            "date": pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]),
            "open": [10, 8, 5],
            "close": [8, 5, 1],
        },
        index=pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]),
    )

    ret = get_event_star(data, Black3())

    assert ret == [Timestamp("2023-01-03 00:00:00")]


def test_event_strategy_instances_do_not_share_state():
    data = pd.DataFrame(
        {
            "open": [10, 8, 5],
            "close": [8, 5, 1],
        },
        index=pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]),
    )

    first = get_event_star(data, Black3())
    second = get_event_star(data, Black3())

    assert first == [Timestamp("2023-01-03 00:00:00")]
    assert second == [Timestamp("2023-01-03 00:00:00")]


def test_get_revenue_by_date_offset():
    data = pd.DataFrame(
        {"price": [10.0, 12.0, 14.0]},
        index=pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]),
    )

    ret = get_revenue_by_date_offset(
        data, [pd.Timestamp("2023-01-01"), pd.Timestamp("2023-01-02")], 2
    )

    assert ret == pytest.approx((10.0 + 12.0) / (14.0 + 14.0))


def test_get_revenue_by_date_offset_requires_events():
    data = pd.DataFrame({"price": [10.0]}, index=pd.to_datetime(["2023-01-01"]))

    with pytest.raises(ValueError, match="date is empty"):
        get_revenue_by_date_offset(data, [], 1)


def test_get_revenue_by_date_offset_requires_positive_offset():
    data = pd.DataFrame({"price": [10.0]}, index=pd.to_datetime(["2023-01-01"]))

    with pytest.raises(ValueError, match="offset should be positive"):
        get_revenue_by_date_offset(data, [pd.Timestamp("2023-01-01")], 0)


def test_get_event_revenue():
    data = pd.DataFrame(
        {
            "price": [10.0, 12.0, 14.0, 10.0, 12.0, 14.0],
            "open": [10.0, 12.0, 14.0, 10.0, 12.0, 14.0],
            "close": [11.0, 14.0, 17.0, 11.0, 14.0, 17.0],
        },
        index=pd.to_datetime(
            [
                "2023-01-01",
                "2023-01-02",
                "2023-01-03",
                "2023-01-04",
                "2023-01-05",
                "2023-01-06",
            ]
        ),
    )

    events = get_event_star(data, Red3())

    assert get_revenue_by_date_offset(data, events, 1) == pytest.approx(
        (14.0 + 14.0) / (10.0 + 14.0)
    )
    assert get_revenue_by_date_offset(data, events, 2) == pytest.approx(
        (14.0 + 14.0) / (12.0 + 14.0)
    )


def test_get_line_uses_requested_window_size():
    data = pd.DataFrame(
        {
            "open": [10, 11, 12, 11, 10],
            "close": [11, 12, 11, 10, 12],
        }
    )

    get_event_line(data, RSILine(), window_size=3)

    strategy = RSILine(window_size=3)
    result = strategy.analysis(data)
    expected_rsi = pd.Series([np.nan, np.nan, 66.666667, 33.333333, 50.0], name="rsi")
    pd.testing.assert_series_equal(result["rsi"], expected_rsi, check_exact=False)


def test_get_line_result_has_one_value_per_row():
    data = pd.DataFrame(
        {
            "open": [10, 11, 12, 11, 10, 12, 13, 12, 11, 13, 14, 13, 12, 14, 15],
            "close": [11, 12, 11, 10, 12, 13, 14, 11, 12, 14, 15, 14, 13, 15, 16],
        }
    )

    result = get_event_line(data, RSILine(), window_size=14)

    assert len(result) == len(data)
    assert result[-1] == pytest.approx(80.0)


def test_get_revenue_by_line_offset_ignores_nan_values():
    data = pd.DataFrame(
        {
            "price": [10.0, 12.0, 14.0, 16.0],
            "rsi": [np.nan, 30.0, 70.0, np.nan],
        }
    )

    assert get_revenue_by_line_offset(data, "rsi", 10) == pytest.approx(12.0 / 14.0)
