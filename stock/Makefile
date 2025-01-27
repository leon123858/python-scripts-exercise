.PHONY: format check-types

# 使用虛擬環境中的可執行文件
VENV = .venv
PYTHON = $(VENV)/bin/python
BLACK = $(VENV)/bin/black
MYPY = $(VENV)/bin/mypy
PIP = $(VENV)/bin/pip

# 格式化代碼
format:
	$(BLACK) ./

# 類型檢查
check-types:
	$(MYPY) --follow-untyped-imports --explicit-package-bases ./

# 同時運行格式化和類型檢查
check: format check-types

freeze:
	$(PIP) freeze > requirements.txt