.PHONY: setup generate-starter generate-full validate test repro detect-anomalies export dashboard report clean help

PYTHON ?= python

help:
	@echo "Available commands:"
	@echo "  make setup            - Install project dependencies in editable mode"
	@echo "  make generate-starter - Run synthetic generator & planning engine with starter scale"
	@echo "  make generate-full    - Run synthetic generator & planning engine with full scale"
	@echo "  make validate         - Run DuckDB SQL and schema validation checks"
	@echo "  make test             - Run pytest test suite"
	@echo "  make repro            - Verify determinism and generate reproducibility report"
	@echo "  make detect-anomalies - Run 5 anomaly injectors and evaluate detector precision/recall"
	@echo "  make export           - Export datasets to CSV, JSON, SQL seed, and SQLite database"
	@echo "  make dashboard        - Launch the interactive Streamlit UI dashboard"
	@echo "  make report           - Generate publication-grade static HTML dashboard (docs/dashboard.html)"
	@echo "  make clean            - Remove build artifacts and temporary caches"

setup:
	$(PYTHON) -m pip install -e .[dev]

generate-starter:
	$(PYTHON) -m oryva_planning.cli generate --config config/starter.yaml

generate-full:
	$(PYTHON) -m oryva_planning.cli generate --config config/full.yaml

validate:
	$(PYTHON) -m oryva_planning.cli validate --config config/starter.yaml

test:
	$(PYTHON) -m pytest tests/

repro:
	$(PYTHON) -m oryva_planning.cli repro --config config/starter.yaml

detect-anomalies:
	$(PYTHON) -m oryva_planning.cli detect-anomalies --config config/starter.yaml

export:
	$(PYTHON) -m oryva_planning.cli export --config config/starter.yaml

dashboard:
	$(PYTHON) -m oryva_planning.cli dashboard

report:
	$(PYTHON) -m oryva_planning.cli report --output docs/dashboard.html

clean:
	$(PYTHON) -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
	$(PYTHON) -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').glob('*.egg-info')]"
