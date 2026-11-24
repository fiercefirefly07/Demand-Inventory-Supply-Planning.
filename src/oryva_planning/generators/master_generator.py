"""
Master Data Generator Orchestrator for Oryva Planning.
Coordinates generation of SKU, Location, Supplier, SkuSupplier, and SkuSubstitute
using SeedSequence.spawn() to preserve strict determinism.
"""

from pathlib import Path
from typing import Dict
import pandas as pd

from oryva_planning.config import PlanningConfig
from oryva_planning.generators.base import SeedStreamManager
from oryva_planning.generators.sku_generator import generate_skus
from oryva_planning.generators.location_generator import generate_locations
from oryva_planning.generators.supplier_generator import generate_suppliers
from oryva_planning.generators.bridge_generator import (
    generate_sku_suppliers,
    generate_sku_substitutes,
)


def generate_master_datasets(
    config: PlanningConfig,
    save_to_disk: bool = True
) -> Dict[str, pd.DataFrame]:
    """
    Generate all master entities and relational bridge tables.
    Returns dictionary mapping table name to validated, sorted pandas DataFrame.
    """
    stream_manager = SeedStreamManager(config.seed)
    rngs = stream_manager.spawn_generators([
        "sku",
        "location",
        "supplier",
        "sku_supplier",
        "sku_substitute",
    ])

    # 1. Master entities
    sku_df = generate_skus(config.scale.num_skus, rngs["sku"], config.year)
    location_df = generate_locations(config.scale.num_locations, rngs["location"], config.year)
    supplier_df = generate_suppliers(config.scale.num_suppliers, rngs["supplier"], config.year)

    # 2. Relational bridge tables using valid parent IDs
    sku_supplier_df = generate_sku_suppliers(
        sku_df,
        supplier_df,
        config.scale.avg_suppliers_per_sku,
        rngs["sku_supplier"],
        config.year,
    )
    sku_substitute_df = generate_sku_substitutes(
        sku_df,
        config.scale.avg_substitutes_per_sku,
        rngs["sku_substitute"],
        config.year,
    )

    datasets = {
        "sku": sku_df,
        "location": location_df,
        "supplier": supplier_df,
        "sku_supplier": sku_supplier_df,
        "sku_substitute": sku_substitute_df,
    }

    if save_to_disk:
        out_dir = Path(config.paths.input_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        for name, df in datasets.items():
            csv_path = out_dir / f"{name}.csv"
            # Deterministic CSV writing: lineterminator '\n', fixed float_format
            df.to_csv(csv_path, index=False, lineterminator="\n", float_format="%.4f")

    return datasets
