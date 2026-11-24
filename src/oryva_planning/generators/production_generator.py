"""
Synthetic Production Plan Generator for Oryva Planning.
Generates manufacturing production batches for Subassemblies and Finished Goods
at Manufacturing Plant locations.
"""

from typing import List
from datetime import date, timedelta
import numpy as np
import pandas as pd

from oryva_planning.schema.enums import ProductionStatus, LocationType, SkuCategory
from oryva_planning.schema.id_builders import build_production_plan_id
from oryva_planning.schema.entities import ProductionPlan
from oryva_planning.generators.base import validate_and_sort_dataframe
from oryva_planning.generators.demand_generator import get_monday_of_week


def generate_production_plans(
    sku_df: pd.DataFrame,
    location_df: pd.DataFrame,
    demand_df: pd.DataFrame,
    num_weeks: int,
    rng: np.random.Generator,
    year: int = 2026,
) -> pd.DataFrame:
    """
    Generate ProductionPlan records.
    - Focuses on manufacturing locations and finished/subassembly SKUs.
    - Output quantity sized to satisfy weekly demand + replenishment.
    - Status reflects execution lifecycle: SCHEDULED, IN_PROGRESS, COMPLETED, or DELAYED.
    """
    # Filter manufacturing locations
    plant_locs = location_df[location_df["type"] == LocationType.MANUFACTURING_PLANT.value]["location_id"].tolist()
    if not plant_locs:
        # Fallback to first location if no explicit plant
        plant_locs = [location_df["location_id"].iloc[0]]

    # Filter manufacturing SKUs (Subassemblies and Finished Goods)
    mfg_skus = sku_df[sku_df["category"].isin([
        SkuCategory.SUBASSEMBLY.value,
        SkuCategory.FINISHED_GOOD.value
    ])]["sku_id"].tolist()

    if not mfg_skus:
        mfg_skus = sku_df["sku_id"].tolist()

    # Pre-calculate aggregate weekly demand per SKU
    sku_wk_demand = demand_df.groupby(["sku_id", "forecast_week"])["forecast_qty"].sum().to_dict()

    plan_rows = []
    plan_seq = 1

    for sku_id in mfg_skus:
        # Assign to 1 or 2 manufacturing plants
        assigned_plants = rng.choice(plant_locs, size=min(len(plant_locs), 2), replace=False)

        for plant_id in assigned_plants:
            for w in range(1, num_weeks + 1):
                week_str = f"{year}W{w:02d}"
                monday_str = get_monday_of_week(year, w)
                run_dt = date.fromisoformat(monday_str) + timedelta(days=int(rng.integers(0, 4)))

                base_demand = sku_wk_demand.get((sku_id, week_str), 100.0)
                planned_output = float(np.round(base_demand * rng.uniform(0.7, 1.3), 2))

                # Status distribution
                if w < 10:
                    status = ProductionStatus.COMPLETED.value
                    actual_output = float(np.round(planned_output * rng.uniform(0.92, 1.05), 2))
                elif w < 25:
                    status = rng.choice(
                        [ProductionStatus.COMPLETED.value, ProductionStatus.DELAYED.value],
                        p=[0.85, 0.15]
                    )
                    actual_output = float(np.round(planned_output * rng.uniform(0.75, 1.02), 2))
                elif w < 30:
                    status = ProductionStatus.IN_PROGRESS.value
                    actual_output = float(np.round(planned_output * rng.uniform(0.30, 0.70), 2))
                else:
                    status = ProductionStatus.SCHEDULED.value
                    actual_output = 0.0

                plan_id = build_production_plan_id(plan_seq, year)
                plan_seq += 1

                created_at_ts = (run_dt - timedelta(days=14)).isoformat() + "T08:00:00Z"

                plan_rows.append({
                    "plan_id": plan_id,
                    "sku_id": sku_id,
                    "location_id": plant_id,
                    "planned_week": week_str,
                    "planned_run_date": run_dt.isoformat(),
                    "planned_output_qty": planned_output,
                    "actual_output_qty": actual_output,
                    "status": str(status),
                    "created_at": created_at_ts,
                })

    df = pd.DataFrame(plan_rows)
    column_order = list(ProductionPlan.model_fields.keys())
    return validate_and_sort_dataframe(df, ProductionPlan, "plan_id", column_order)
