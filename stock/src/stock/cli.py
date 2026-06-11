import argparse

import twstock

from stock.data import get_stock_data_cached
from stock.reports import write_result_csv
from stock.runner import run_strategy


def update_stock_codes() -> None:
    twstock.__update_codes()
    for stock_id in twstock.codes:
        print(stock_id)


def main() -> None:
    parser = argparse.ArgumentParser(prog="stock")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("init", help="Update and print twstock stock codes")
    cache_parser = subparsers.add_parser("cache", help="Fetch and cache stock data")
    cache_parser.add_argument("--stock-id", required=True)
    cache_parser.add_argument("--start-year", type=int)
    cache_parser.add_argument("--start-month", type=int)
    cache_parser.add_argument("--refresh", action="store_true")

    run_parser = subparsers.add_parser("run", help="Run a workspace strategy")
    run_parser.add_argument("--strategy", required=True)
    run_parser.add_argument("--stock-id", required=True)
    run_parser.add_argument("--start-year", type=int)
    run_parser.add_argument("--start-month", type=int)
    run_parser.add_argument("--output")
    run_parser.add_argument("--initial-cash", type=float, default=1_000_000.0)
    run_parser.add_argument("--commission-rate", type=float, default=0.001425)
    run_parser.add_argument("--tax-rate", type=float, default=0.003)
    run_parser.add_argument("--execution-delay-days", type=int, default=1)
    run_parser.add_argument(
        "--execution-price",
        choices=["open", "high", "low", "close", "price"],
        default="open",
    )
    run_parser.add_argument("--lot-size", type=int, default=1)

    args = parser.parse_args()

    if args.command == "init":
        update_stock_codes()
    elif args.command == "cache":
        data = get_stock_data_cached(
            args.stock_id,
            start_year=args.start_year,
            start_month=args.start_month,
            refresh=args.refresh,
        )
        print(f"cached {args.stock_id}: {len(data)} rows")
    elif args.command == "run":
        result = run_strategy(
            args.strategy,
            stock_id=args.stock_id,
            start_year=args.start_year,
            start_month=args.start_month,
            initial_cash=args.initial_cash,
            commission_rate=args.commission_rate,
            tax_rate=args.tax_rate,
            execution_delay_days=args.execution_delay_days,
            execution_price=args.execution_price,
            lot_size=args.lot_size,
        )
        if args.output:
            write_result_csv(result.backtest, args.output)
            print(f"wrote {args.output}")
        else:
            print(result.backtest.summary.to_string(index=False))
            if not result.backtest.trades.empty:
                print(result.backtest.trades.tail().to_string(index=False))
    else:
        print("hello")
