PYTHON ?= python3

.PHONY: test schema
test:
	PYTHONPATH=apps/server $(PYTHON) -m unittest discover -s tests -v
	PYTHONPATH=apps/server $(PYTHON) scripts/export_schema.py --check

schema:
	PYTHONPATH=apps/server $(PYTHON) scripts/export_schema.py
