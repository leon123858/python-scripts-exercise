import argparse

import twstock


def update_stock_codes() -> None:
    twstock.__update_codes()
    for stock_id in twstock.codes:
        print(stock_id)


def main() -> None:
    parser = argparse.ArgumentParser(prog="stock")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("init", help="Update and print twstock stock codes")

    args = parser.parse_args()

    if args.command == "init":
        update_stock_codes()
    else:
        print("hello")
