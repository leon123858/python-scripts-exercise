# AI Init

This project is a Python stock-analysis exercise that uses `uv` for environment and dependency management.

## Project Overview

- Runtime: Python 3.13, pinned by `.python-version`.
- Dependency source: `pyproject.toml`.
- Lockfile: `uv.lock`.
- CLI entrypoint: `stock`, implemented in `src/stock/cli.py`.
- Source code: `src/stock/`.
- Tests: `tests/`.

The code fetches Taiwan stock data through `twstock`, converts it into `pandas.DataFrame` objects, applies event/line strategies, calculates simple revenue ratios, and draws charts with `matplotlib` / `mplfinance`.

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
- Mark tests touching real `twstock` network calls with `@pytest.mark.integration`.
- Keep generated caches such as `.venv`, `.pytest_cache`, `.mypy_cache`, and `__pycache__` out of source control.
