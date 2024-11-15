# Makefile
# 設定 Python 執行檔
PYTHON = python
# 測試目錄
TEST_DIR = tests
# install tool
PKG_MANAGE = pip

all:
	make type
	make format
	make start

test:
	$(PYTHON) -m unittest discover -s $(TEST_DIR) -p '*_test.py'

start:
	$(PYTHON) main.py

type:
	mypy .

format:
	black .
	isort .
	flake8 --ignore=E501 --extend-exclude .venv,dist

freeze:
	$(PKG_MANAGE) freeze > requirements.txt

install:
	$(PKG_MANAGE) install -r requirements.txt
