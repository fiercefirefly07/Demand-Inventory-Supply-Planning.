"""
Multi-Format Exporters for Oryva Planning.
Exports planning datasets to:
1. CSV (primary, deterministic with fixed column order and LF terminators)
2. JSON (records format, ISO timestamps)
3. SQL Seed (ANSI SQL INSERT DML script)
4. SQLite (Single-file relational database with tables and primary keys)
5. Source Manifest (fully synthetic provenance audit metadata)
"""

from pathlib import Path
import json
import sqlite3
from typing import Dict, Any
import pandas as pd

from oryva_planning.config import PlanningConfig
from oryva_planning.schema.data_dictionary import generate_sql_ddl


def export_csv(datasets: Dict[str, pd.DataFrame], output_dir: Path) -> Dict[str, Path]:
    """Export all tables as deterministic CSV files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, df in datasets.items():
        csv_path = output_dir / f"{name}.csv"
        df.to_csv(csv_path, index=False, lineterminator="\n", float_format="%.4f")
        paths[name] = csv_path
    return paths


def export_json(datasets: Dict[str, pd.DataFrame], output_dir: Path) -> Dict[str, Path]:
    """Export all tables as JSON records files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, df in datasets.items():
        json_path = output_dir / f"{name}.json"
        # Convert NaN to None for clean JSON serialization
        clean_records = json.loads(df.to_json(orient="records", date_format="iso"))
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(clean_records, f, indent=2)
        paths[name] = json_path
    return paths


def export_sql_seed(datasets: Dict[str, pd.DataFrame], output_file: Path) -> Path:
    """Generate ANSI SQL seed file containing DDL and INSERT statements."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    ddl = generate_sql_ddl()
    dml_lines = [
        "-- Oryva AI Synthetic Supply Chain Planning Dataset",
        "-- Fully Synthetic Data Seed Script",
        "",
        ddl,
        "",
        "BEGIN TRANSACTION;",
        ""
    ]

    for name, df in datasets.items():
        table_name = name.lower()
        cols = list(df.columns)
        cols_str = ", ".join(cols)

        # Batch inserts in chunks of 500
        for i in range(0, len(df), 500):
            chunk = df.iloc[i:i + 500]
            val_rows = []
            for _, row in chunk.iterrows():
                row_vals = []
                for col in cols:
                    val = row[col]
                    if pd.isna(val):
                        row_vals.append("NULL")
                    elif isinstance(val, (int, float)):
                        row_vals.append(str(val))
                    elif isinstance(val, bool):
                        row_vals.append("1" if val else "0")
                    else:
                        clean_str = str(val).replace("'", "''")
                        row_vals.append(f"'{clean_str}'")
                val_rows.append(f"({', '.join(row_vals)})")

            if val_rows:
                stmt = f"INSERT INTO {table_name} ({cols_str}) VALUES\n" + ",\n".join(val_rows) + ";"
                dml_lines.append(stmt)
                dml_lines.append("")

    dml_lines.append("COMMIT;")

    output_file.write_text("\n".join(dml_lines), encoding="utf-8")
    return output_file


def export_sqlite(datasets: Dict[str, pd.DataFrame], output_file: Path) -> Path:
    """Export all datasets into a single-file SQLite database."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    if output_file.exists():
        output_file.unlink()

    conn = sqlite3.connect(output_file)

    # 1. Execute DDL
    ddl = generate_sql_ddl()
    conn.executescript(ddl)

    # 2. Insert records
    for name, df in datasets.items():
        table_name = name.lower()
        df.to_sql(table_name, conn, if_exists="append", index=False)

    conn.commit()
    conn.close()
    return output_file


def export_source_manifest(
    output_file: Path,
    config: PlanningConfig,
    datasets: Dict[str, pd.DataFrame],
) -> Path:
    """Export provenance and source manifest JSON file."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    table_summaries = {}
    total_records = 0
    for name, df in datasets.items():
        row_count = len(df)
        total_records += row_count
        table_summaries[name] = {
            "row_count": row_count,
            "columns": list(df.columns),
            "primary_key": df.columns[0] if len(df.columns) > 0 else "N/A",
        }

    manifest = {
        "project": "Oryva AI - Demand, Inventory & Supply Planning",
        "provenance": "Fully synthetic, no external data",
        "license": "MIT",
        "deadline": "2026-11-25",
        "generator_seed": config.seed,
        "planning_year": config.year,
        "planning_horizon_weeks": config.planning_horizon_weeks,
        "scale": config.scale.name,
        "total_records_generated": total_records,
        "tables": table_summaries,
        "distributions_used": {
            "demand": "Vectorized Pareto lognormal + annual seasonality + spike weeks",
            "supplier_lead_time": "Gamma distribution with unreliability tail",
            "sku_costs": "Category-specific lognormal with markup selling price",
            "facility_capacities": "Uniform scaled across hub, regional, and plant tiers"
        }
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return output_file
