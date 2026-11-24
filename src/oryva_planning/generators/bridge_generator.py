"""
Synthetic Bridge Table Generators: SkuSupplier and SkuSubstitute.
Establishes many-to-many relationship structures with business rules:
- Guaranteed primary supplier per SKU.
- Category-compatible substitutes with approval flags.
"""

from typing import List, Tuple
import numpy as np
import pandas as pd

from oryva_planning.schema.id_builders import (
    build_sku_supplier_id,
    build_sku_substitute_id,
)
from oryva_planning.schema.entities import SkuSupplier, SkuSubstitute
from oryva_planning.generators.base import validate_and_sort_dataframe


def generate_sku_suppliers(
    sku_df: pd.DataFrame,
    supplier_df: pd.DataFrame,
    avg_suppliers_per_sku: int,
    rng: np.random.Generator,
    year: int = 2026,
) -> pd.DataFrame:
    """
    Generate SkuSupplier bridge records.
    - Every SKU gets at least 1 qualified supplier.
    - Exactly one supplier is marked `is_primary=True` per SKU.
    - Composite primary key: SKUSUP-<sku_id>-<supplier_id>.
    """
    sku_ids = sku_df["sku_id"].tolist()
    all_supplier_ids = supplier_df["supplier_id"].tolist()
    num_suppliers_total = len(all_supplier_ids)

    rows = []
    for sku_id in sku_ids:
        # Determine how many suppliers to assign (1 to min(num_suppliers_total, max(1, avg_suppliers_per_sku + 1)))
        max_possible = min(num_suppliers_total, max(1, avg_suppliers_per_sku * 2))
        k = int(rng.integers(1, max_possible + 1))

        # Sample k unique suppliers
        chosen_indices = rng.choice(num_suppliers_total, size=k, replace=False)
        chosen_suppliers = [all_supplier_ids[idx] for idx in chosen_indices]

        # First chosen is primary
        for idx, sup_id in enumerate(chosen_suppliers):
            is_primary = (idx == 0)
            part_num = f"VND-{sup_id[-4:]}-{sku_id[-4:]}"
            bridge_id = build_sku_supplier_id(sku_id, sup_id)

            rows.append({
                "sku_supplier_id": bridge_id,
                "sku_id": sku_id,
                "supplier_id": sup_id,
                "is_primary": is_primary,
                "supplier_part_number": part_num,
                "effective_start_date": f"{year}-01-01",
                "effective_end_date": f"{year}-12-31",
            })

    df = pd.DataFrame(rows)
    column_order = list(SkuSupplier.model_fields.keys())
    return validate_and_sort_dataframe(df, SkuSupplier, "sku_supplier_id", column_order)


def generate_sku_substitutes(
    sku_df: pd.DataFrame,
    avg_substitutes_per_sku: int,
    rng: np.random.Generator,
    year: int = 2026,
) -> pd.DataFrame:
    """
    Generate SkuSubstitute bridge records with approval flags.
    - Group SKUs by category to ensure meaningful substitutes.
    - No self-substitution (primary != substitute).
    - In clean baseline, all generated substitutes are approved=True.
    - Composite primary key: SUB-<primary_sku>-<substitute_sku>.
    """
    rows = []
    # Group by category for realistic substitution compatibility
    grouped = sku_df.groupby("category")["sku_id"].apply(list).to_dict()

    for category, category_sku_ids in grouped.items():
        n_in_cat = len(category_sku_ids)
        if n_in_cat <= 1:
            continue

        for sku_id in category_sku_ids:
            # Determine number of substitutes for this SKU
            k = int(rng.integers(0, min(n_in_cat - 1, avg_substitutes_per_sku * 2) + 1))
            if k == 0:
                continue

            # Candidate substitutes from the same category excluding self
            candidates = [s for s in category_sku_ids if s != sku_id]
            chosen_substitutes = rng.choice(candidates, size=min(k, len(candidates)), replace=False)

            for sub_sku_id in chosen_substitutes:
                sub_id = build_sku_substitute_id(sku_id, sub_sku_id)
                # Conversion rate (typically 1.0, occasionally 0.8 to 1.25)
                conv_rate = float(np.round(rng.choice([1.0, 1.0, 1.0, 0.8, 1.2]), 2))

                rows.append({
                    "substitute_id": sub_id,
                    "primary_sku_id": sku_id,
                    "substitute_sku_id": sub_sku_id,
                    "conversion_rate": conv_rate,
                    "approved": True,  # Baseline is approved; anomalies will inject unapproved records
                    "effective_start_date": f"{year}-01-01",
                    "effective_end_date": f"{year}-12-31",
                })

    if not rows:
        # Fallback if catalog was extremely small
        df = pd.DataFrame(columns=list(SkuSubstitute.model_fields.keys()))
        return df

    df = pd.DataFrame(rows)
    # Deduplicate by primary key in case of accidental repeats
    df = df.drop_duplicates(subset=["substitute_id"]).reset_index(drop=True)

    column_order = list(SkuSubstitute.model_fields.keys())
    return validate_and_sort_dataframe(df, SkuSubstitute, "substitute_id", column_order)
