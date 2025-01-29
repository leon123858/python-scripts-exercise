import pandas as pd
from pandas import Timestamp

from src.events.event_star import EveningStar, Black3, get_event_star, Red3
from src.utils.revenue import get_revenue_by_date_offset


def test_evening_star_analysis():
    # Sample data
    data = pd.DataFrame(
        {
            "date": pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]),
            "open": [10, 12, 9],
            "close": [8, 11, 15],
        }
    )

    # Create EveningStar strategy
    strategy = EveningStar()

    # Analyze the data
    analyzed_data = strategy.analysis(data.copy())

    # Expected values for K_size, big_k, is_up
    expected_big_k = pd.Series([False, False, True])
    expected_is_up = pd.Series([False, False, True])

    # Assert the analyzed data
    assert analyzed_data["big_k"].eq(expected_big_k).all()
    assert analyzed_data["is_up"].eq(expected_is_up).all()


def test_catch_event():
    data = pd.DataFrame(
        {
            "date": pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]),
            "open": [10, 8, 5],
            "close": [8, 5, 1],
        },
        index=pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]),
    )
    strategy = Black3()
    ret = get_event_star(data, strategy)
    assert len(ret) == 1
    assert ret[0] == Timestamp("2023-01-03 00:00:00")


def test_get_revenue():
    data = pd.DataFrame(
        {
            "date": pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]),
            "price": [10.0, 12.0, 14.0],
        },
        index=pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]),
    )
    ret = get_revenue_by_date_offset(
        data, [pd.Timestamp("2023-01-01"), pd.Timestamp("2023-01-02")], 2
    )
    assert ret == ((10.0 + 12.0) / (14.0 + 14.0))


def test_get_event_revenue():
    data = pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2023-01-01",
                    "2023-01-02",
                    "2023-01-03",
                    "2023-01-04",
                    "2023-01-05",
                    "2023-01-06",
                ]
            ),
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
    strategy = Red3()
    events = get_event_star(data, strategy)
    ret = []
    for i in range(1, 3):
        ret.append(get_revenue_by_date_offset(data, events, i))
    assert ret[0] == ((14.0 + 14.0) / (10.0 + 14.0))
    assert ret[1] == ((14.0 + 14.0) / (12.0 + 14.0))
