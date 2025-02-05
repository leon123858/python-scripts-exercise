# 啟動 .venv 虛擬環境
.\.venv\Scripts\activate

# 格式化代碼
black ./

# 類型檢查
mypy --follow-untyped-imports --explicit-package-bases ./
