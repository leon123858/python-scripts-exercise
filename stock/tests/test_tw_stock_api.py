import pytest
from src.tables.initDataFrame import get_stock_data


def test_get_stock_data_invalid():
    with pytest.raises(ValueError, match="should set year and month same time or not"):
        get_stock_data("2330", 0)
    with pytest.raises(KeyError, match="9999"):
        get_stock_data("9999")
