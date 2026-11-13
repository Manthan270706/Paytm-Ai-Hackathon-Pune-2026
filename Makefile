.PHONY: all guard test lint check

all: guard lint test

guard:
	python scripts/guard.py

lint:
	python -m ruff check services/api/app
	python -m mypy services/api/app

test:
	python -m pytest services/api/app/tests -v

check: guard lint test
