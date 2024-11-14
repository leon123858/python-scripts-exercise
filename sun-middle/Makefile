all:
	make type
	make format
	make start

test:
	python -m unittest discover -s utils -p '*_test.py'

start:
	python main.py

type:
	mypy .

format:
	black .
	isort .
	flake8 --extend-exclude .venv,dist

freeze:
	pip freeze > requirements.txt

install:
	pip install -r requirements.txt
