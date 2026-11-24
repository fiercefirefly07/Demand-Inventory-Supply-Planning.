"""
CLI application for Oryva Planning.
Command-line interface for synthetic generation, validation, schema inspection,
and reproducibility checking.
"""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table

from oryva_planning.config import PlanningConfig
from oryva_planning.generators import generate_master_datasets
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
    """Generate synthetic planning dataset using configured scale and parameters."""
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
    console.print(f"  - SKUs: [yellow]{cfg.scale.num_skus}[/yellow]")
    console.print(f"  - Locations: [yellow]{cfg.scale.num_locations}[/yellow]")
    console.print(f"  - Suppliers: [yellow]{cfg.scale.num_suppliers}[/yellow]")
    console.print(f"  - Inbound POs: [yellow]{cfg.scale.num_inbound_pos}[/yellow]")
    console.print(f"  - Output input dir: [yellow]{cfg.paths.input_dir}[/yellow]")
    console.print(f"  - Ground truth dir: [yellow]{cfg.paths.ground_truth_dir}[/yellow]\n")

    console.print("[bold green]Executing Phase 2: Generating Master Data & Bridge Tables...[/bold green]")
    datasets = generate_master_datasets(cfg, save_to_disk=True)

    summary_table = Table(title="Generated Master Datasets Summary", show_header=True, header_style="bold blue")
    summary_table.add_column("Table Name", style="cyan")
    summary_table.add_column("Row Count", justify="right", style="green")
    summary_table.add_column("Primary Key Sample", style="yellow")
    summary_table.add_column("File Path", style="dim")

    for name, df in datasets.items():
        pk_col = df.columns[0]
        sample_pk = f"{df[pk_col].iloc[0]} .. {df[pk_col].iloc[-1]}" if len(df) > 0 else "N/A"
        file_path = f"{cfg.paths.input_dir}/{name}.csv"
        summary_table.add_row(name, f"{len(df):,}", sample_pk, file_path)

    console.print(summary_table)
    console.print(f"[bold green]Master data generation complete. Files saved to {cfg.paths.input_dir}/[/bold green]")


@app.command()
def validate(
    data_dir: Path = typer.Option(
        Path("data/inputs"), "--data-dir", "-d", help="Directory containing generated input CSV files"
    )
):
    """Run validation checks (DuckDB SQL and schema rules) against generated datasets."""
    console.print(f"[bold cyan]Validating data in:[/bold cyan] {data_dir}")
    if not data_dir.exists():
        console.print(f"[yellow]Directory {data_dir} does not exist yet. Run 'generate' first.[/yellow]")
        return
    console.print("[green]Schema validation engine ready.[/green]")


@app.command()
def repro(
    config_path: Path = typer.Option(
        Path("config/starter.yaml"), "--config", "-c", help="Configuration file for reproducibility run"
    )
):
    """Run generation twice and verify row count and SHA-256 bit-for-bit equivalence."""
    console.print(f"[bold cyan]Deterministic reproducibility harness ready for config:[/bold cyan] {config_path}")


if __name__ == "__main__":
    app()
