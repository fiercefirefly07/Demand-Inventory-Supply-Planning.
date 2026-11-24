"""
Synthetic Inventory Generator for Oryva Planning.
Generates baseline opening stock, safety stocks, and reorder points
calibrated against SKU demand levels.
"""

from typing import Dict, List
import numpy as np
import pandas as pd

from oryva_planning.schema.enums import InventoryStatus
from oryva_planning.schema.id_builders import build_inventory_id
from oryva_planning.schema.entities import Inventory
from oryva_planning.generators.base import validate_and_sort_dataframe


def generate_inventory(
    sku_df: pd.DataFrame,
    location_df: pd.DataFrame,
    demand_df: pd.DataFrame,
    rng: np.random.Generator,
    year: int = 2026,
) -> pd.DataFrame:
    """
    Generate deterministic opening Inventory for every SKU-location pair.
    - Safety stock: ~1.5 weeks of mean demand
    - Reorder point: Safety stock + 2 weeks lead time buffer
    - On-hand stock: Uniformly distributed between 0.5x and 2.5x of safety stock
    - 5% initial stockouts to create realistic early shortage test cases
    """
    sku_ids = sku_df["sku_id"].tolist()
    loc_ids = location_df["location_id"].tolist()
    sku_uom_map = dict(zip(sku_df["sku_id"], sku_df["unit_of_measure"]))

    # Calculate average weekly demand per SKU-Location pair
    avg_demand = (
        demand_df.groupby(["sku_id", "location_id"])["forecast_qty"]
        .mean()
        .to_dict()
    )

    rows = []
    for s_idx, sku_id in enumerate(sku_ids):
        uom = sku_uom_map[sku_id]
        for l_idx, loc_id in enumerate(loc_ids):
            inv_id = build_inventory_id(sku_id, loc_id)
            mean_wk_demand = avg_demand.get((sku_id, loc_id), 50.0)

            # Safety stock: 1.2x to 1.8x average weekly demand
            safety_stock = round(float(mean_wk_demand * rng.uniform(1.2, 1.8)), 2)

            # Reorder point: safety stock + 1.5 to 2.5 weeks lead time demand
            reorder_point = round(float(safety_stock + mean_wk_demand * rng.uniform(1.5, 2.5)), 2)

            # Opening on-hand quantity:
            # 5% chance of initial stockout (on_hand = 0)
            is_initial_stockout = (rng.random() < 0.05)
            if is_initial_stockout:
                on_hand = 0.0
            else:
                # Normal distribution around 1.5x safety stock
                on_hand = round(float(np.maximum(0.0, safety_stock * rng.uniform(0.6, 2.2))), 2)

            # Status: 97% AVAILABLE, 2% QUARANTINE, 1% RESERVED
            status = rng.choice(
                [InventoryStatus.AVAILABLE.value, InventoryStatus.QUARANTINE.value, InventoryStatus.RESERVED.value],
                p=[0.97, 0.02, 0.01]
            )

            rows.append({
                "inventory_id": inv_id,
                "sku_id": sku_id,
                "location_id": loc_id,
                "on_hand_qty": on_hand,
                "safety_stock_qty": safety_stock,
                "reorder_point": reorder_point,
                "unit_of_measure": str(uom),
                "effective_date": f"{year}-01-01",
                "status": str(status),
            })

    df = pd.DataFrame(rows)
    column_order = list(Inventory.model_fields.keys())
    return validate_and_sort_dataframe(df, Inventory, "inventory_id", column_order)
