SWIFT_DIR = ../readalign-swift

.PHONY: install test lint format sync-yaml

install:
	python3 -m venv venv
	venv/bin/pip install -q -r requirements.txt
	venv/bin/pip install -q -e .

test:
	venv/bin/pytest readalign/ -q
	venv/bin/pytest test_readme.py -q

lint:
	venv/bin/ruff check readalign/
	venv/bin/ruff format --check readalign/

format:
	venv/bin/ruff check --fix readalign/
	venv/bin/ruff format readalign/

sync-yaml:
	cp $(SWIFT_DIR)/Sources/ReadAlign/Resources/rules.yaml readalign/rules.yaml
	cp $(SWIFT_DIR)/Tests/ReadAlignTests/Resources/*.yaml readalign/cases/
