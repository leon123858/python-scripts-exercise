import pandas as pd
from pandas import Timestamp

from src.events.event_star import EveningStar, Black3, get_event_star
from src.tables.initDataFrame import get_stock_data


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
        }
    )
    strategy = Black3()
    ret = get_event_star(data, strategy)
    assert len(ret) == 1
    assert ret[0] == Timestamp('2023-01-03 00:00:00')