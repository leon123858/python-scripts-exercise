"""
@auther Leon Lin
@date 2025/01/28
"""

import twstock
from src.tables.initDataFrame import get_stock_data


def init():
    twstock.__update_codes()


def main():
    df2330 = get_stock_data("2330")
    print(df2330.tail(5))


if __name__ == "__main__":
    main()
