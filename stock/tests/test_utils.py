from src.utils.tables import create_dataframe_from_lists
import pytest
import pandas as pd


def test_create_dataframe_valid_input():
    """測試正常輸入情況"""
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
    """測試列表長度不一致的情況"""
    list1 = [1, 2, 3]
    list2 = ["a", "b"]
    columns = ["num", "char"]
    with pytest.raises(ValueError, match="all list len should same"):
        create_dataframe_from_lists(list1, list2, columns=columns)


def test_create_dataframe_no_columns():
    """測試沒有提供欄位名稱的情況"""
    list1 = [1, 2, 3]
    list2 = ["a", "b", "c"]
    with pytest.raises(ValueError, match="should have col name"):
        create_dataframe_from_lists(list1, list2)


def test_create_dataframe_wrong_column_length():
    """測試欄位名稱長度不正確的情況"""
    list1 = [1, 2, 3]
    list2 = ["a", "b", "c"]
    columns = ["num"]
    with pytest.raises(ValueError, match="col name len not right"):
        create_dataframe_from_lists(list1, list2, columns=columns)


def test_create_dataframe_empty_lists():
    """測試輸入空列表的情況"""
    list1 = []
    list2 = []
    columns = ["num", "char"]
    df = create_dataframe_from_lists(list1, list2, columns=columns)
    assert isinstance(df, pd.DataFrame)
    assert df.empty  # 檢查 DataFrame 是否為空
    assert list(df.columns) == columns
