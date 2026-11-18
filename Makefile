.PHONY: install build test-build test lint format docs

install:
	python3 -m venv venv
	venv/bin/pip install -q -r requirements.txt
	venv/bin/pip install -q -e .

build:
	venv/bin/python3 -m build --wheel

test-build:
	venv/bin/python3 -m compileall -q readalign tests

test:
	venv/bin/pytest tests/ -q
	venv/bin/pytest test_readme.py -q

lint:
	venv/bin/ruff check .
	venv/bin/ruff format --check .

format:
	venv/bin/ruff check --fix .
	venv/bin/ruff format .

docs:
	venv/bin/pdoc readalign -o build/docs
