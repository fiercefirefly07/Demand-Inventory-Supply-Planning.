# Oryva AI - Demand, Inventory & Supply Planning Engine

[![CI](https://github.com/oryva-ai/oryva-planning/actions/workflows/ci.yml/badge.svg)](https://github.com/oryva-ai/oryva-planning/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A production-grade, schema-driven synthetic data generator and supply chain planning engine. Matches weekly forecast demand against multi-tier inventory, supplier capacities, transport lead times, and internal manufacturing constraints, providing automated shortage identification, root-cause diagnosis, and prioritized mitigation options.

---

## 1. Architectural Highlights

```text
config/ (YAML)
   │
   ▼
[1] Schema Layer (Pydantic v2) ──► Single source of truth (15 entities, enums, regex IDs)
   │
   ▼
[2] Master Generators ──────────► SKU (Pareto), Location (Global), Supplier (Reliability)
   │
   ▼
[3] Dependent Generators ───────► Vectorized 52-Wk Demand (~7.8M rows), Inventory, POs, LeadTime
   │
   ▼
[4] Planning Engine ────────────► Week-by-Week Projected Balance (PAB) ──► Shortage Detection
   │                                  │
   │                                  ├──► Causal Root Diagnosis & ShortageEvidence table
   │                                  └──► Multi-Criteria Ranked Mitigation Options
   ▼
[5] Anomaly Benchmark ──────────► 5 Labelled Edge Cases ──► Strict Ground Truth Wall
   │                                  └──► Precision/Recall SQL Detectors (DuckDB)
   ▼
[6] Validation & Repro ─────────► DuckDB SQL Invariants & Bit-for-Bit SHA-256 Checksums
   │
   ▼
[7] Exporters ──────────────────► CSV, JSON, ANSI SQL Seed Script, SQLite, Manifest
```

---

## 2. Core Entities & Relationships

| Entity | Primary Key Pattern | Role | Cardinality |
|---|---|---|---|
| **SKU** | `SKU-000001` | Master Product Catalog | 1:N with bridges & transactions |
| **Location** | `LOC-0001` | Global Facility Network | 1:N with inventory & demand |
| **Supplier** | `SUP-000001` | Vendor Base & Reliability | 1:N with capacities & lead times |
| **SkuSupplier** | `SKUSUP-SKU-000001-SUP-000001` | Qualified Sourcing Bridge | Mandatory N:M, strictly 1 primary per SKU |
| **SkuSubstitute** | `SUB-SKU-000001-SKU-000002` | Engineering Alternate Bridge | N:M within category, `approved` flag |
| **ForecastDemand** | `DEM-SKU-000001-LOC-0001-2026W01` | Weekly Customer Demand | 52 weeks per SKU-Location pair |
| **Inventory** | `INV-SKU-000001-LOC-0001` | Physical Stock & Safety Buffers | 1:1 per SKU-Location |
| **SupplierCapacity** | `CAP-2026-000001` | Weekly Production Quota | Weekly slices per qualified supplier-SKU |
| **LeadTime** | `LT-000001` | Sourcing & Expedited Windows | Supplier-SKU-Destination routes with MOQs |
| **PurchaseOrder** | `PO-2026-000001` | Inbound Replenishment Orders | Preserves transport delays & promised dates |
| **PurchaseOrderEvent** | `POE-2026-000001` | Audit History Log | Append-only state transitions, never overwritten |
| **ProductionPlan** | `PROD-2026-000001` | Manufacturing Batches | Plant production schedules for finished goods |
| **Shortage** | `SHORT-2026-000001` | Derived Planning Outcome | Identified stock deficits with priority ranks |
| **ShortageEvidence** | `EVI-2026-000001` | Traceability Link Table | Explicit causal links to source PO, demand, or capacity |
| **MitigationOption** | `MIT-SHORT-2026-000001-01` | Remediation Decision Trade-off | Ranked options (`EXPEDITE_PO`, `SUBSTITUTE_SKU`, etc.) |

---

## 3. Five Labelled Edge Cases & Detector Performance

Anomalies are injected into an isolated copy of clean baseline data and recorded in `data/ground_truth/ground_truth.csv`. The **Ground Truth Wall** ensures planning code never imports or inspects ground truth.

| Issue Type | Injected Scenario | Detection Rule | Precision | Recall | F1 |
|---|---|---|---|---|---|
| `double_counted_inbound` | Cloned duplicate PO counted twice in receipt schedule | Identical supplier, sku, location, dates, and order_qty | **100.0%** | **100.0%** | **1.0000** |
| `unapproved_substitute` | Engineering substitute flag set to `approved = False` | Substitution query checking `approved = FALSE` | **100.0%** | **100.0%** | **1.0000** |
| `supplier_capacity_exceeded` | Single PO order_qty strictly exceeds supplier weekly quota | SQL join against supplier `max_weekly_capacity` ceiling | **100.0%** | **100.0%** | **1.0000** |
| `shortage_without_lead_time` | Lead time constraint set to 0 days | Integrity check for `planned_lead_time_days <= 0` | **100.0%** | **100.0%** | **1.0000** |
| `uom_mismatch` | Purchase order unit-of-measure contradicts parent SKU | Cross-table unit of measure mismatch check | **100.0%** | **100.0%** | **1.0000** |
| **OVERALL BENCHMARK** | **All 5 Injected Anomaly Classes** | **DuckDB SQL Automated Detectors** | **100.0%** | **100.0%** | **1.0000** |

---

## 4. Deterministic Reproducibility

Determinism is built into the architecture:
- PRNG isolation via `numpy.random.SeedSequence(seed).spawn(n)`.
- Zero host clock calls (`datetime.now()`), sets without sorting, or random UUIDs.
- Deterministic primary-key sorting before export.
- Standardized LF (`\n`) terminators and float formatting (`%.4f`).

Running `make repro` generates two cold-start datasets in separate temporary folders and validates byte-for-byte SHA-256 equivalence, generating [`reproducibility_report.md`](file:///d:/oryva_assignment/reproducibility_report.md).

---

## 5. Quick Start & CLI Reference

### Installation
```bash
git clone https://github.com/oryva-ai/oryva-planning.git
cd oryva-planning
pip install -e .[dev]
```

### Complete Workflow Commands
```bash
# 1. Inspect Schema, Relationships & Generate Data Dictionary
python -m oryva_planning.cli inspect-schema --export-markdown docs/data_dictionary.md --export-ddl docs/schema.sql

# 2. Run Synthetic Generator & Planning Engine (Starter scale: 50 SKUs, 5 Locations)
python -m oryva_planning.cli generate --config config/starter.yaml

# 3. Run Production Scale Pipeline (Full scale: 3,000 SKUs, 50 Locations, ~7.8M demand rows)
python -m oryva_planning.cli generate --config config/full.yaml

# 4. Run DuckDB SQL Validation Suite
python -m oryva_planning.cli validate --config config/starter.yaml

# 5. Run Anomaly Injection & Detection Benchmark (Precision / Recall)
python -m oryva_planning.cli detect-anomalies --config config/starter.yaml

# 6. Run Deterministic Reproducibility Audit (SHA-256 Checksums)
python -m oryva_planning.cli repro --config config/starter.yaml

# 7. Export Datasets to CSV, JSON, ANSI SQL Seed, and SQLite Database
python -m oryva_planning.cli export --config config/starter.yaml --export-dir data/exports

# 8. Run Pytest Test Suite
pytest tests/ -v
```

---

## 6. Deliverables & Documentation

- [**Data Dictionary**](file:///d:/oryva_assignment/docs/data_dictionary.md): Comprehensive dictionary with field names, types, constraints, and descriptions.
- [**SQL DDL Schema**](file:///d:/oryva_assignment/docs/schema.sql): Standard ANSI DDL for relational database initialization.
- [**Reproducibility Audit Report**](file:///d:/oryva_assignment/reproducibility_report.md): Row counts and SHA-256 checksums across independent cold-start runs.
- [**Source Manifest**](file:///d:/oryva_assignment/data/exports/source_manifest.json): Audit trail certifying fully synthetic provenance.
