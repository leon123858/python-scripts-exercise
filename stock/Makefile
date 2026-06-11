.PHONY: help sync lock clean test test-local test-integration format lint typecheck check run init

PYTHON := uv run python

help:
	@echo Common uv-based commands:
	@echo   make sync       Install dependencies from uv.lock
	@echo   make lock       Rebuild uv.lock from pyproject.toml
	@echo   make clean      Remove local caches
	@echo   make test       Run the full pytest suite
	@echo   make test-local Run tests that do not require network access
	@echo   make test-integration Run tests that require live services
	@echo   make format     Format Python files with black
	@echo   make lint       Run flake8
	@echo   make typecheck  Run mypy
	@echo   make check      Run format check, lint, typecheck, and local tests
	@echo   make run        Run the default app entrypoint
	@echo   make init       Update and print twstock codes

sync:
	uv sync --frozen

lock:
	uv lock

clean:
	$(PYTHON) -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; shutil.rmtree('.pytest_cache', ignore_errors=True); shutil.rmtree('.mypy_cache', ignore_errors=True); shutil.rmtree('.ruff_cache', ignore_errors=True)"

test:
	$(PYTHON) -m pytest -q

test-local:
	$(PYTHON) -m pytest -q -m "not integration"

test-integration:
	$(PYTHON) -m pytest -q -m integration

format:
	uv run black src tests

lint:
	uv run flake8 src tests --max-line-length=88 --extend-ignore=E203

typecheck:
	uv run mypy -p stock
	uv run mypy tests

check:
	uv run black --check src tests
	uv run flake8 src tests --max-line-length=88 --extend-ignore=E203
	uv run mypy -p stock
	uv run mypy tests
	$(PYTHON) -m pytest -q -m "not integration"

run:
	uv run stock

init:
	uv run stock init
