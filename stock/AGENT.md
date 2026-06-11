# AI Init

This project is a Python stock-analysis exercise that uses `uv` for environment and dependency management.

## Project Overview

- Runtime: Python 3.13, pinned by `.python-version`.
- Dependency source: `pyproject.toml`.
- Lockfile: `uv.lock`.
- CLI entrypoint: `stock`, implemented in `src/stock/cli.py`.
- Source code: `src/stock/`.
- Tests: `tests/`.

The code fetches Taiwan stock data through `twstock`, caches it as CSV, lets users write strategies in `src/workspace/`, generates signals, runs daily backtests, and returns report DataFrames/CSV.

## Common Commands

Use `make` targets instead of ad hoc scripts.

- `make sync`: install dependencies from `uv.lock`.
- `make lock`: rebuild `uv.lock` from `pyproject.toml`.
- `make test`: run the full pytest suite, including integration tests.
- `make test-local`: run tests that avoid live network access.
- `make test-integration`: run tests that require live external services.
- `make format`: format with Black.
- `make lint`: run Flake8.
- `make typecheck`: run Mypy.
- `make check`: run format check, lint, typecheck, and local tests.
- `make run`: run the `stock` CLI.
- `make init`: run `stock init`.
- `make clean`: remove local Python/test caches.

## Development Notes

- Prefer `uv run ...` for Python commands so tools use the project environment.
- Do not add separate shell or PowerShell helper scripts for routine commands; put common workflows in `Makefile`.
- Keep import paths rooted at the installed package name, `stock`, not at raw folders under `src`.
- User strategies should live outside `src/stock`, usually in `src/workspace`, and should inherit `stock.BaseStrategy`.
- Mark tests touching real `twstock` network calls with `@pytest.mark.integration`.
- Keep generated caches such as `.venv`, `.pytest_cache`, `.mypy_cache`, and `__pycache__` out of source control.

## Strategy Backtest Workflow For Agents

The normal user flow is: the user describes a trading strategy in natural language, then the agent implements that strategy in this framework and backtests it against requested Taiwan stock IDs.

When handling a strategy request:

- Read the existing framework before editing:
  - Strategy examples: `src/workspace/strategies.py`.
  - Strategy interface: `src/stock/core.py`.
  - Signal helpers and sizing: `src/stock/signals.py`.
  - Backtest behavior: `src/stock/backtest.py`.
  - CLI runner: `src/stock/cli.py` and `src/stock/runner.py`.
- Implement user strategies in `src/workspace/strategies.py` unless the user asks for a different organization.
- Add or update focused tests under `tests/`, preferably avoiding live network calls by injecting small DataFrames into `run_strategy`.
- Run `make test-local` for ordinary strategy changes. Run `make check` before considering framework-level changes complete.
- If the user asks for concrete stock backtests, run the CLI and write reports under `reports/`.

Strategy classes should inherit `BaseStrategy`:

```python
from stock import BaseStrategy
from stock.signals import SizeType, buy, sell


class MyStrategy(BaseStrategy):
    name = "my_strategy"

    def prepare(self, context):
        data = context.data.copy()
        # Add indicators or pattern columns here.
        return data

    def generate_signals(self, context):
        data = context.prepared_data
        if data is None:
            return []
        return [
            buy(
                "2024-01-02",
                reason="example entry",
                size_type=SizeType.CASH_PERCENT,
                size_value=0.5,
            ),
            sell("2024-01-03", reason="example exit", size_type=SizeType.ALL),
        ]
```

Signals support position sizing. Use the sizing model instead of hard-coding all-in behavior inside strategies:

- `SizeType.ALL`: buy with all cash or sell the whole position.
- `SizeType.CASH_PERCENT`: buy using a percentage of current cash, where `size_value=0.5` means 50%.
- `SizeType.CASH_AMOUNT`: buy or sell approximately a fixed cash amount.
- `SizeType.SHARES`: buy or sell a fixed number of shares.
- `SizeType.POSITION_PERCENT`: sell a percentage of the current position.

Backtests default to a more conservative daily execution model: signals execute
on the next trading day's open (`execution_delay_days=1`,
`execution_price="open"`). The old same-day close behavior is still available
with `execution_delay_days=0` and `execution_price="close"`. On BUY signals the
engine calculates affordable shares from current cash, price, commission, and
`lot_size`. On SELL signals it calculates shares from the current position.
Trade reports include `date`, `signal_date`, `gross`, `fee`, `tax`, `cash`,
`size_type`, and `size_value`.

Useful CLI commands:

```powershell
uv run stock run --strategy workspace.strategies:MyStrategy --stock-id 2330
uv run stock run --strategy workspace.strategies:MyStrategy --stock-id 2330 --output reports/my_strategy_2330.csv
uv run stock run --strategy workspace.strategies:MyStrategy --stock-id 8299 --output reports/my_strategy_8299.csv
uv run stock run --strategy workspace.strategies:MyStrategy --stock-id 2330 --execution-delay-days 0 --execution-price close --commission-rate 0 --tax-rate 0
```

When reporting results to the user, include:

- Strategy class name and where it was implemented.
- Key assumptions or parameter defaults chosen from the user's description.
- Test command results.
- Backtest stock ID, date range, final equity, total return, trade count, and win rate.
- Paths to generated summary/trades/equity CSV files when reports were written.
