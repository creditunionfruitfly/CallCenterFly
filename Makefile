.PHONY: install validate test lint package train evaluate infer smoke

install:
	python -m pip install -e '.[dev,serve]'

validate:
	callcenterfly validate-data --dataset data/synthetic/v0.1.0

test:
	python -m pytest

lint:
	python -m ruff check .

package:
	python -m build

train:
	callcenterfly train --dataset data/synthetic/v0.1.0 --output models/mock-baseline-v0

evaluate:
	callcenterfly evaluate --dataset data/synthetic/v0.1.0 --model models/mock-baseline-v0 --split test

infer:
	callcenterfly infer --dataset data/synthetic/v0.1.0 --model models/mock-baseline-v0 --decision-id SYN-CU-010-CU004-001-D2

smoke:
	python scripts/smoke_test.py
