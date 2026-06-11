# Stock

Taiwan stock research framework for fetching daily data, writing custom
strategies, generating signals, and running simple backtests.

## Setup

```powershell
make sync
```

## Common Commands

```powershell
make test-local
make test-integration
make format
make lint
make typecheck
make check
make run
```

`make test-local` avoids tests that require live `twstock` network access.

## Run A Strategy

Create strategies under `src/workspace/` and import the framework from `stock`.

```powershell
uv run stock run --strategy workspace.strategies:RsiReversalStrategy --stock-id 2330
uv run stock run --strategy workspace.strategies:RsiReversalStrategy --stock-id 2330 --output reports/rsi_2330.csv
```

Cache stock data explicitly:

```powershell
uv run stock cache --stock-id 2330 --start-year 2023 --start-month 1
```

Strategy shape:

```python
from stock import BaseStrategy
from stock.signals import buy, sell


class MyStrategy(BaseStrategy):
    name = "my_strategy"

    def prepare(self, context):
        return context.data

    def generate_signals(self, context):
        return [buy("2024-01-02"), sell("2024-01-03")]
```
