from pathlib import Path

import pandas as pd

from stock import cli


def test_cli_run_writes_csv(monkeypatch, tmp_path, capsys):
    output = tmp_path / "summary.csv"

    def fake_run_strategy(*args, **kwargs):
        from stock.backtest import BacktestResult
        from stock.runner import AnalysisResult
        from stock.core import StrategyContext

        data = pd.DataFrame({"date": pd.to_datetime(["2024-01-01"])})
        backtest = BacktestResult(
            trades=pd.DataFrame(),
            equity_curve=pd.DataFrame(),
            summary=pd.DataFrame(
                [
                    {
                        "stock_id": "2330",
                        "strategy": "fake",
                        "start_date": "2024-01-01",
                        "end_date": "2024-01-01",
                        "initial_cash": 1000.0,
                        "final_equity": 1000.0,
                        "total_return": 0.0,
                        "trade_count": 0,
                        "win_rate": 0.0,
                    }
                ]
            ),
        )
        return AnalysisResult(
            context=StrategyContext("2330", data),
            signals=pd.DataFrame(),
            backtest=backtest,
        )

    monkeypatch.setattr(cli, "run_strategy", fake_run_strategy)
    monkeypatch.setattr(
        "sys.argv",
        [
            "stock",
            "run",
            "--strategy",
            "workspace.strategies:RsiReversalStrategy",
            "--stock-id",
            "2330",
            "--output",
            str(output),
        ],
    )

    cli.main()

    assert output.exists()
    assert Path(str(output).replace(".csv", "_trades.csv")).exists()
    assert "wrote" in capsys.readouterr().out
