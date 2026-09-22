PYTHON ?= .venv/bin/python

.PHONY: test schema check dev format audit
test:
	PYTHONPATH=apps/server $(PYTHON) -m unittest discover -s tests -v
	PYTHONPATH=apps/server $(PYTHON) scripts/export_schema.py --check
	npm run types:check
	PYTHON=$(PYTHON) npm test

schema:
	PYTHONPATH=apps/server $(PYTHON) scripts/export_schema.py
	npm run types

check: test
	$(PYTHON) -m ruff check apps/server scripts tests
	$(PYTHON) -m ruff format --check apps/server scripts tests
	$(PYTHON) -m mypy
	npm run build

dev:
	$(PYTHON) scripts/dev.py

format:
	$(PYTHON) -m ruff check --fix apps/server scripts tests
	$(PYTHON) -m ruff format apps/server scripts tests

audit:
	$(PYTHON) -m pip_audit -r requirements.lock
	npm audit
