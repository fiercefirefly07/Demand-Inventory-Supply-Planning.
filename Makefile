.PHONY: setup generate-starter generate-full validate test repro clean help

PYTHON ?= python

help:
	@echo "Available commands:"
	@echo "  make setup            - Install project dependencies in editable mode"
	@echo "  make generate-starter - Run synthetic generator with starter scale"
	@echo "  make generate-full    - Run synthetic generator with full scale"
	@echo "  make validate         - Run SQL and schema validation checks"
	@echo "  make test             - Run pytest test suite"
	@echo "  make repro            - Verify determinism and generate reproducibility report"
	@echo "  make clean            - Remove build artifacts and temporary caches"

setup:
	$(PYTHON) -m pip install -e .[dev]

generate-starter:
	$(PYTHON) -m oryva_planning.cli generate --config config/starter.yaml

generate-full:
	$(PYTHON) -m oryva_planning.cli generate --config config/full.yaml

validate:
	$(PYTHON) -m oryva_planning.cli validate --data-dir data/inputs

test:
	$(PYTHON) -m pytest tests/

repro:
	$(PYTHON) -m oryva_planning.cli repro --config config/starter.yaml

clean:
	$(PYTHON) -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
	$(PYTHON) -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').glob('*.egg-info')]"
