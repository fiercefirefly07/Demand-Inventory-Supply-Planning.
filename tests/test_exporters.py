"""
Unit tests for Phase 8 Multi-Format Exporters.
Verifies CSV, JSON, ANSI SQL seed, SQLite database, and Source Manifest exports.
"""

from pathlib import Path
import json
import sqlite3
import pandas as pd
import pytest

from oryva_planning.config import PlanningConfig
from oryva_planning.generators import generate_all_datasets
from oryva_planning.planning import run_planning_engine
from oryva_planning.export import (
    export_csv,
    export_json,
    export_sql_seed,
    export_sqlite,
    export_source_manifest,
)


@pytest.fixture
def starter_config() -> PlanningConfig:
    return PlanningConfig.load_from_yaml("config/starter.yaml")


class TestExporters:
    """Verify multi-format export operations."""

    def test_export_all_formats(self, starter_config: PlanningConfig, tmp_path: Path):
        datasets = generate_all_datasets(starter_config, save_to_disk=False)
        planning = run_planning_engine(datasets, starter_config, save_to_disk=False)
        all_tables = {**datasets, **planning}

        # 1. CSV
        csv_dir = tmp_path / "csv"
        csv_paths = export_csv(all_tables, csv_dir)
        for name, p in csv_paths.items():
            assert p.exists()
            assert p.stat().st_size > 0

        # 2. JSON
        json_dir = tmp_path / "json"
        json_paths = export_json(all_tables, json_dir)
        for name, p in json_paths.items():
            assert p.exists()
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                assert len(data) == len(all_tables[name])

        # 3. SQL Seed
        sql_file = tmp_path / "sql" / "seed_data.sql"
        sql_path = export_sql_seed(all_tables, sql_file)
        assert sql_path.exists()
        sql_text = sql_path.read_text(encoding="utf-8")
        assert "CREATE TABLE" in sql_text
        assert "INSERT INTO" in sql_text
        assert "COMMIT;" in sql_text

        # 4. SQLite
        sqlite_file = tmp_path / "sqlite" / "test.db"
        sqlite_path = export_sqlite(all_tables, sqlite_file)
        assert sqlite_path.exists()

        # Connect and query SQLite
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sku")
        sku_count = cursor.fetchone()[0]
        assert sku_count == starter_config.scale.num_skus

        cursor.execute("SELECT COUNT(*) FROM purchaseorder")
        po_count = cursor.fetchone()[0]
        assert po_count == starter_config.scale.num_inbound_pos
        conn.close()

        # 5. Manifest
        manifest_file = tmp_path / "source_manifest.json"
        manifest_path = export_source_manifest(manifest_file, starter_config, all_tables)
        assert manifest_path.exists()
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
            assert manifest_data["provenance"] == "Fully synthetic, no external data"
            assert manifest_data["generator_seed"] == starter_config.seed
