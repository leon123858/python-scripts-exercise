import pandas as pd
import pytest

from stock.utils.tables import create_dataframe_from_lists


def test_create_dataframe_valid_input():
    list1 = [1, 2, 3]
    list2 = ["a", "b", "c"]
    columns = ["num", "char"]

    df = create_dataframe_from_lists(list1, list2, columns=columns)

    assert isinstance(df, pd.DataFrame)
    assert df.shape == (3, 2)
    assert list(df.columns) == columns
    assert df["num"].tolist() == list1
    assert df["char"].tolist() == list2


def test_create_dataframe_different_lengths():
    with pytest.raises(ValueError, match="all list len should same"):
        create_dataframe_from_lists([1, 2, 3], ["a", "b"], columns=["num", "char"])


def test_create_dataframe_no_columns():
    with pytest.raises(ValueError, match="should have col name"):
        create_dataframe_from_lists([1, 2, 3], ["a", "b", "c"])


def test_create_dataframe_wrong_column_length():
    with pytest.raises(ValueError, match="col name len not right"):
        create_dataframe_from_lists([1, 2, 3], ["a", "b", "c"], columns=["num"])


def test_create_dataframe_empty_lists():
    df = create_dataframe_from_lists([], [], columns=["num", "char"])

    assert isinstance(df, pd.DataFrame)
    assert df.empty
    assert list(df.columns) == ["num", "char"]
