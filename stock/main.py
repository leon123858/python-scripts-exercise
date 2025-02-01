"""
@auther Leon Lin
@date 2025/01/28
"""

import sys
import twstock

from src.events.events import get_event_line
from src.events.lines import RSILine
from src.tables.initDataFrame import get_stock_data
from src.utils.revenue import get_revenue_by_line_offset


def init():
    twstock.__update_codes()
    all_stocks = twstock.codes
    for key in all_stocks:
        print(key)


def main():
    print("hello")


if __name__ == "__main__":
    print("---start---")
    if len(sys.argv) > 1:
        if sys.argv[1] == "init":
            print("init tw stock code")
            init()
        else:
            print("not exist this sub command")
    else:
        main()
    print("---end---")
