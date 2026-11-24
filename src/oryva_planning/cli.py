"""
CLI application for Oryva Planning.
Command-line interface for synthetic data generation, supply chain planning,
DuckDB SQL validation, anomaly detection benchmarks, and reproducibility auditing.
"""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table

from oryva_planning.config import PlanningConfig
from oryva_planning.generators import generate_all_datasets
from oryva_planning.planning import run_planning_engine
from oryva_planning.anomalies import inject_anomalies, evaluate_anomaly_detection
from oryva_planning.validation import DuckDBValidationSuite, run_reproducibility_check
from oryva_planning.export import (
    export_csv,
    export_json,
    export_sql_seed,
    export_sqlite,
    export_source_manifest,
)
from oryva_planning.schema import (
    CORE_ENTITIES,
    ENTITY_RELATIONSHIPS,
    generate_markdown_data_dictionary,
    generate_sql_ddl,
)

app = typer.Typer(
    name="oryva-planning",
    help="Oryva AI - Demand, Inventory & Supply Planning Engine CLI",
    add_completion=False,
)
console = Console()


@app.command()
def inspect_schema(
    export_markdown: Optional[Path] = typer.Option(
        None, "--export-markdown", "-m", help="Path to write generated markdown data dictionary"
    ),
    export_ddl: Optional[Path] = typer.Option(
        None, "--export-ddl", "-d", help="Path to write generated SQL DDL statements"
    ),
):
    """Inspect the schema layer: registered entities, fields, relationships, and constraints."""
    console.print("[bold cyan]Oryva Planning - Registered Schema Entities[/bold cyan]\n")

    table = Table(title="Core Entities & Relational Bridge Tables", show_header=True, header_style="bold magenta")
    table.add_column("Entity Name", style="cyan", width=22)
    table.add_column("Fields Count", justify="right", width=14)
    table.add_column("Primary Key Pattern", style="green", width=34)

    pk_patterns = {
        "SKU": "SKU-000001",
        "Location": "LOC-0001",
        "Supplier": "SUP-000001",
        "SkuSupplier": "SKUSUP-SKU-000001-SUP-000001",
        "SkuSubstitute": "SUB-SKU-000001-SKU-000002",
        "ForecastDemand": "DEM-SKU-000001-LOC-0001-2026W01",
        "Inventory": "INV-SKU-000001-LOC-0001",
        "SupplierCapacity": "CAP-2026-000001",
        "LeadTime": "LT-000001",
        "PurchaseOrder": "PO-2026-000001",
        "PurchaseOrderEvent": "POE-2026-000001",
        "ProductionPlan": "PROD-2026-000001",
        "Shortage": "SHORT-2026-000001",
        "ShortageEvidence": "EVI-2026-000001",
        "MitigationOption": "MIT-SHORT-2026-000001-01",
    }

    for name, model in CORE_ENTITIES.items():
        table.add_row(
            name,
            str(len(model.model_fields)),
            pk_patterns.get(name, "Deterministic ID")
        )

    console.print(table)

    rel_table = Table(title="\nEntity Cardinalities & Dependencies", show_header=True, header_style="bold blue")
    rel_table.add_column("Parent", style="yellow")
    rel_table.add_column("Child", style="green")
    rel_table.add_column("Cardinality", justify="center")
    rel_table.add_column("Role / Type")

    for rel in ENTITY_RELATIONSHIPS:
        rel_table.add_row(rel["parent"], rel["child"], rel["cardinality"], rel["type"])

    console.print(rel_table)

    if export_markdown:
        export_markdown.parent.mkdir(parents=True, exist_ok=True)
        md_content = generate_markdown_data_dictionary()
        export_markdown.write_text(md_content, encoding="utf-8")
        console.print(f"\n[green]Saved Markdown Data Dictionary to:[/green] {export_markdown}")

    if export_ddl:
        export_ddl.parent.mkdir(parents=True, exist_ok=True)
        ddl_content = generate_sql_ddl()
        export_ddl.write_text(ddl_content, encoding="utf-8")
        console.print(f"[green]Saved SQL DDL to:[/green] {export_ddl}")


@app.command()
def generate(
    config_path: Path = typer.Option(
        Path("config/starter.yaml"), "--config", "-c", help="Path to YAML configuration file"
    ),
    scale: Optional[str] = typer.Option(
        None, "--scale", "-s", help="Scale override ('starter' or 'full')"
    ),
    seed: Optional[int] = typer.Option(
        None, "--seed", help="Random seed override"
    ),
):
    """Run full synthetic generation and planning engine pipeline."""
    if scale:
        config_path = Path(f"config/{scale}.yaml")

    console.print(f"[bold cyan]Loading configuration from:[/bold cyan] {config_path}")
    cfg = PlanningConfig.load_from_yaml(config_path)
    if seed is not None:
        cfg.seed = seed

    console.print(f"[bold green]Config loaded successfully:[/bold green]")
    console.print(f"  - Scale: [yellow]{cfg.scale.name}[/yellow]")
    console.print(f"  - Seed: [yellow]{cfg.seed}[/yellow]")
    console.print(f"  - Horizon: [yellow]{cfg.planning_horizon_weeks} weeks ({cfg.year})[/yellow]")
    console.print(f"  - Output input dir: [yellow]{cfg.paths.input_dir}[/yellow]\n")

    console.print("[bold green]Stage 1: Generating Master & Dependent Datasets...[/bold green]")
    datasets = generate_all_datasets(cfg, save_to_disk=True)

    console.print("[bold green]Stage 2: Running Planning Engine (Balance, Shortages, Mitigations)...[/bold green]")
    planning_results = run_planning_engine(datasets, cfg, save_to_disk=True)

    all_tables = {**datasets, **planning_results}

    summary_table = Table(title="Generated Pipeline Datasets Summary", show_header=True, header_style="bold blue")
    summary_table.add_column("Table Name", style="cyan")
    summary_table.add_column("Row Count", justify="right", style="green")
    summary_table.add_column("Primary Key Sample", style="yellow")
    summary_table.add_column("File Path", style="dim")

    for name, df in all_tables.items():
        pk_col = df.columns[0]
        sample_pk = f"{df[pk_col].iloc[0]} .. {df[pk_col].iloc[-1]}" if len(df) > 0 else "N/A"
        file_path = f"{cfg.paths.input_dir}/{name}.csv"
        summary_table.add_row(name, f"{len(df):,}", sample_pk, file_path)

    console.print(summary_table)
    console.print(f"\n[bold green]Success! All pipeline files saved to {cfg.paths.input_dir}/[/bold green]")


@app.command()
def validate(
    config_path: Path = typer.Option(
        Path("config/starter.yaml"), "--config", "-c", help="Configuration file"
    )
):
    """Run DuckDB SQL integrity suite (PK uniqueness, FK integrity, arithmetic, lifecycles)."""
    cfg = PlanningConfig.load_from_yaml(config_path)
    console.print(f"[bold cyan]Running DuckDB SQL Validation Suite for scale: {cfg.scale.name}[/bold cyan]\n")

    datasets = generate_all_datasets(cfg, save_to_disk=False)
    planning_results = run_planning_engine(datasets, cfg, save_to_disk=False)
    all_tables = {**datasets, **planning_results}

    suite = DuckDBValidationSuite(all_tables)
    summary = suite.run_all_checks()
    suite.close()

    table = Table(title="DuckDB SQL Validation Results", show_header=True, header_style="bold magenta")
    table.add_column("Check Category", style="cyan", width=26)
    table.add_column("Rule / Relationship", style="white", width=42)
    table.add_column("Status", justify="center", width=10)
    table.add_column("Details", style="dim")

    for r in summary["results"]:
        status_text = "[green]PASS[/green]" if r["passed"] else "[red]FAIL[/red]"
        target = r.get("table") or r.get("relationship") or r.get("rule")
        table.add_row(r["check"], str(target), status_text, r["details"])

    console.print(table)
    if summary["all_passed"]:
        console.print(f"\n[bold green]ALL {summary['total_checks']} SQL INTEGRITY CHECKS PASSED![/bold green]")
    else:
        console.print(f"\n[bold red]{summary['failed_checks']} CHECKS FAILED![/bold red]")


@app.command()
def detect_anomalies(
    config_path: Path = typer.Option(
        Path("config/starter.yaml"), "--config", "-c", help="Configuration file"
    )
):
    """Inject 5 labelled anomalies, run detectors, and report Precision/Recall metrics."""
    cfg = PlanningConfig.load_from_yaml(config_path)
    console.print(f"[bold cyan]Running Anomaly Injection & Detection Benchmark...[/bold cyan]\n")

    clean_datasets = generate_all_datasets(cfg, save_to_disk=False)
    injected_datasets, gt_df = inject_anomalies(clean_datasets, cfg, save_ground_truth=True)

    console.print(f"[green]Injected {len(gt_df)} anomalies into isolated copy and wrote to {cfg.paths.ground_truth_dir}/ground_truth.csv[/green]")

    eval_results = evaluate_anomaly_detection(injected_datasets, gt_df)

    table = Table(title="Anomaly Detection Performance (Precision / Recall)", show_header=True, header_style="bold blue")
    table.add_column("Anomaly Issue Type", style="cyan", width=28)
    table.add_column("TP", justify="right", width=6)
    table.add_column("FP", justify="right", width=6)
    table.add_column("FN", justify="right", width=6)
    table.add_column("Precision", justify="right", style="green", width=12)
    table.add_column("Recall", justify="right", style="green", width=12)
    table.add_column("F1-Score", justify="right", style="yellow", width=12)

    for issue, m in eval_results["by_issue"].items():
        table.add_row(
            issue,
            str(m["tp"]),
            str(m["fp"]),
            str(m["fn"]),
            f"{m['precision'] * 100:.1f}%",
            f"{m['recall'] * 100:.1f}%",
            f"{m['f1']:.4f}",
        )

    overall = eval_results["overall"]
    table.add_section()
    table.add_row(
        "[bold]OVERALL BENCHMARK[/bold]",
        str(overall["tp"]),
        str(overall["fp"]),
        str(overall["fn"]),
        f"[bold]{overall['precision'] * 100:.1f}%[/bold]",
        f"[bold]{overall['recall'] * 100:.1f}%[/bold]",
        f"[bold]{overall['f1']:.4f}[/bold]",
    )

    console.print(table)


@app.command()
def repro(
    config_path: Path = typer.Option(
        Path("config/starter.yaml"), "--config", "-c", help="Configuration file for reproducibility run"
    ),
    report_path: Path = typer.Option(
        Path("reproducibility_report.md"), "--report-path", "-r", help="Output Markdown report path"
    )
):
    """Run generation twice and verify row count and SHA-256 bit-for-bit equivalence."""
    console.print(f"[bold cyan]Running Deterministic Reproducibility Audit...[/bold cyan]")
    is_reproducible = run_reproducibility_check(config_path, report_path)
    if is_reproducible:
        console.print(f"[bold green]DETERMINISM VERIFIED: All SHA-256 checksums match bit-for-bit![/bold green]")
        console.print(f"Report written to: [yellow]{report_path}[/yellow]")
    else:
        console.print(f"[bold red]DETERMINISM CHECK FAILED![/bold red]")


@app.command()
def export(
    config_path: Path = typer.Option(
        Path("config/starter.yaml"), "--config", "-c", help="Configuration file"
    ),
    export_dir: Path = typer.Option(
        Path("data/exports"), "--export-dir", "-e", help="Target export directory"
    )
):
    """Export datasets to CSV, JSON, SQL seed script, and SQLite database."""
    cfg = PlanningConfig.load_from_yaml(config_path)
    console.print(f"[bold cyan]Exporting all datasets to multiple formats in {export_dir}...[/bold cyan]")

    datasets = generate_all_datasets(cfg, save_to_disk=False)
    planning_results = run_planning_engine(datasets, cfg, save_to_disk=False)
    all_tables = {**datasets, **planning_results}

    # 1. CSV export
    csv_paths = export_csv(all_tables, export_dir / "csv")
    console.print(f"  - CSV files exported to: [yellow]{export_dir / 'csv'}[/yellow]")

    # 2. JSON export
    json_paths = export_json(all_tables, export_dir / "json")
    console.print(f"  - JSON files exported to: [yellow]{export_dir / 'json'}[/yellow]")

    # 3. SQL Seed script
    sql_path = export_sql_seed(all_tables, export_dir / "sql" / "seed_data.sql")
    console.print(f"  - SQL Seed script created at: [yellow]{sql_path}[/yellow]")

    # 4. SQLite database
    sqlite_path = export_sqlite(all_tables, export_dir / "sqlite" / "oryva_planning.db")
    console.print(f"  - SQLite database built at: [yellow]{sqlite_path}[/yellow]")

    # 5. Provenance Manifest
    manifest_path = export_source_manifest(export_dir / "source_manifest.json", cfg, all_tables)
    console.print(f"  - Source manifest generated at: [yellow]{manifest_path}[/yellow]")

    console.print(f"\n[bold green]Multi-format exports completed successfully![/bold green]")


if __name__ == "__main__":
    app()
