"""
Synthetic Supplier Capacity and Lead Time Generator for Oryva Planning.
Generates:
1. Weekly supplier capacity records (including constrained capacity bottlenecks).
2. Sourcing lead times with Gamma distribution and MOQ/Order Multiple constraints.
"""

from typing import Tuple, List, Dict
import numpy as np
import pandas as pd

from oryva_planning.schema.id_builders import (
    build_supplier_capacity_id,
    build_lead_time_id,
)
from oryva_planning.schema.entities import SupplierCapacity, LeadTime
from oryva_planning.generators.base import validate_and_sort_dataframe


def generate_capacity_and_lead_times(
    sku_supplier_df: pd.DataFrame,
    supplier_df: pd.DataFrame,
    location_df: pd.DataFrame,
    demand_df: pd.DataFrame,
    num_weeks: int,
    rng: np.random.Generator,
    year: int = 2026,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate SupplierCapacity and LeadTime records based on valid SKU-Supplier relationships.
    - Capacity: Weekly slices per SKU-Supplier pair.
      15% of suppliers are capacity-constrained (max capacity near or below total demand).
    - LeadTime: Gamma distributed lead time days per Supplier-SKU-Destination triple.
      Unreliable suppliers have extended lead times.
    """
    supplier_rel_map = dict(zip(supplier_df["supplier_id"], supplier_df["reliability_score"]))
    loc_ids = location_df["location_id"].tolist()

    # Pre-calculate aggregate weekly demand per SKU
    sku_weekly_demand = demand_df.groupby(["sku_id", "forecast_week"])["forecast_qty"].sum().to_dict()
    sku_avg_weekly_demand = demand_df.groupby("sku_id")["forecast_qty"].mean().to_dict()

    # -------------------------------------------------------------
    # 1. Supplier Capacity Records
    # -------------------------------------------------------------
    capacity_rows = []
    cap_seq = 1

    # Unique SKU-Supplier pairs
    unique_pairs = sku_supplier_df[["sku_id", "supplier_id", "is_primary"]].drop_duplicates().to_dict("records")

    for pair in unique_pairs:
        sku_id = pair["sku_id"]
        sup_id = pair["supplier_id"]
        is_primary = pair["is_primary"]

        base_demand = sku_avg_weekly_demand.get(sku_id, 100.0)
        rel_score = supplier_rel_map.get(sup_id, 0.95)

        # 15% chance this supplier is severely capacity constrained
        is_constrained = (rng.random() < 0.15)
        if is_constrained:
            cap_multiplier = rng.uniform(0.70, 1.05)
        elif is_primary:
            cap_multiplier = rng.uniform(1.40, 2.80)
        else:
            cap_multiplier = rng.uniform(0.90, 1.80)

        nominal_capacity = float(np.round(max(1500.0, base_demand * 8.0) * cap_multiplier, 2))

        for w in range(1, num_weeks + 1):
            week_str = f"{year}W{w:02d}"
            # Small weekly variation in capacity (+/- 8%)
            week_cap = float(np.round(nominal_capacity * rng.uniform(0.92, 1.08), 2))
            cap_id = build_supplier_capacity_id(cap_seq, year)
            cap_seq += 1

            capacity_rows.append({
                "capacity_id": cap_id,
                "supplier_id": sup_id,
                "sku_id": sku_id,
                "period_week": week_str,
                "max_weekly_capacity": week_cap,
                "committed_qty": 0.0,
                "available_capacity": week_cap,
                "effective_start_date": f"{year}-01-01",
                "effective_end_date": f"{year}-12-31",
            })

    df_capacity = pd.DataFrame(capacity_rows)
    cap_order = list(SupplierCapacity.model_fields.keys())
    df_capacity = validate_and_sort_dataframe(df_capacity, SupplierCapacity, "capacity_id", cap_order)

    # -------------------------------------------------------------
    # 2. Lead Time Records (Supplier -> SKU -> Destination Location)
    # -------------------------------------------------------------
    lead_time_rows = []
    lt_seq = 1

    for pair in unique_pairs:
        sku_id = pair["sku_id"]
        sup_id = pair["supplier_id"]
        rel_score = supplier_rel_map.get(sup_id, 0.95)

        # Baseline gamma-distributed lead time: shape=3.5, scale=4.5 -> mean ~16 days
        base_lt = rng.gamma(shape=3.5, scale=4.5)
        if rel_score < 0.85:
            # Unreliable suppliers have longer, more variable lead times
            base_lt += rng.uniform(7.0, 15.0)

        # Minimum order quantity (MOQ) and order multiple
        moq = float(rng.choice([50.0, 100.0, 200.0, 500.0]))
        order_multiple = float(rng.choice([10.0, 25.0, 50.0]))

        # Destination locations: sample a subset of locations for each supplier
        # In starter (5 locs), all locations; in full (50 locs), 5-15 locations
        n_dest_locs = min(len(loc_ids), int(rng.integers(3, min(15, len(loc_ids)) + 1)))
        chosen_locs = rng.choice(loc_ids, size=n_dest_locs, replace=False)

        for dest_loc in chosen_locs:
            lt_days = max(3, int(np.round(base_lt + rng.uniform(-2, 4))))
            exp_lt_days = max(2, int(np.round(lt_days * rng.uniform(0.25, 0.45))))
            lt_id = build_lead_time_id(lt_seq)
            lt_seq += 1

            lead_time_rows.append({
                "lead_time_id": lt_id,
                "supplier_id": sup_id,
                "sku_id": sku_id,
                "destination_location_id": dest_loc,
                "planned_lead_time_days": lt_days,
                "minimum_order_qty": moq,
                "order_multiple_qty": order_multiple,
                "expedited_lead_time_days": exp_lt_days,
                "effective_start_date": f"{year}-01-01",
                "effective_end_date": f"{year}-12-31",
            })

    df_lead_time = pd.DataFrame(lead_time_rows)
    lt_order = list(LeadTime.model_fields.keys())
    df_lead_time = validate_and_sort_dataframe(df_lead_time, LeadTime, "lead_time_id", lt_order)

    return df_capacity, df_lead_time
