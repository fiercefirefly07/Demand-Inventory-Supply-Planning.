# Oryva AI - Demand, Inventory & Supply Planning Engine

Deterministic synthetic data generator and supply chain planning engine matching forecast demand to inventory, supplier capacity, lead times, and production constraints, with automated shortage identification, root-cause diagnosis, and prioritized mitigations.

## Tech Stack
- **Python 3.11+**
- **Data Modeling & Validation:** Pydantic v2, DuckDB SQL
- **Vectorized Math:** NumPy (`default_rng`, `SeedSequence.spawn`), Pandas
- **Testing:** Pytest
- **CLI & Automation:** Typer, Rich, YAML, GNU Make
- **CI:** GitHub Actions

## Architecture (Layered Pipeline)
```text
config -> schema layer -> generators -> planning engine -> anomaly injector
-> validators -> exporters
```

## Quick Start

### 1. Setup
```bash
pip install -e .[dev]
```

### 2. Inspect Schema & Generate Data Dictionary
```bash
python -m oryva_planning.cli inspect-schema --export-markdown docs/data_dictionary.md --export-ddl docs/schema.sql
```

### 3. Run Tests
```bash
pytest tests/ -v
```
