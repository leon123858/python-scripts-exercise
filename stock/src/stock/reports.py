from pathlib import Path

import pandas as pd

from stock.backtest import BacktestResult


def summary_to_dataframe(result: BacktestResult) -> pd.DataFrame:
    return result.summary.copy()


def write_result_csv(result: BacktestResult, output: str | Path) -> None:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.summary.to_csv(output_path, index=False)
    result.trades.to_csv(
        output_path.with_name(f"{output_path.stem}_trades.csv"), index=False
    )
    result.equity_curve.to_csv(
        output_path.with_name(f"{output_path.stem}_equity.csv"), index=False
    )
