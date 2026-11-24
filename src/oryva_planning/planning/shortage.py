"""
Shortage Identification and Prioritization Engine for Oryva Planning.
Derives shortage incidents from projected inventory deficits, calculates
unmet demand quantities, and computes priority scores and horizon-wide ranks.
"""

from typing import List, Dict, Tuple
import pandas as pd
import numpy as np

from oryva_planning.schema.enums import ShortageStatus
from oryva_planning.schema.id_builders import build_shortage_id
from oryva_planning.generators.demand_generator import get_monday_of_week


def identify_and_prioritize_shortages(
    balance_df: pd.DataFrame,
    sku_df: pd.DataFrame,
    location_df: pd.DataFrame,
    year: int = 2026,
) -> pd.DataFrame:
    """
    Identify weeks where projected balance < 0.
    Computes:
    - shortage_qty: magnitude of stock deficit
    - unmet_demand_qty: demand portion left unfulfilled
    - cumulative_shortage_qty: accumulated deficit across planning horizon
    - priority_score: multi-criteria severity (0 to 100)
    - priority_rank: 1..N based on priority_score descending
    """
    sku_price_map = dict(zip(sku_df["sku_id"], sku_df["selling_price"]))
    loc_type_weights = {
        "CENTRAL_HUB": 1.4,
        "REGIONAL_DC": 1.2,
        "MANUFACTURING_PLANT": 1.3,
        "SATELLITE_WH": 1.0,
    }
    loc_type_map = dict(zip(location_df["location_id"], location_df["type"]))

    # Filter deficit weeks
    deficit_df = balance_df[balance_df["projected_balance"] < 0].copy()

    if deficit_df.empty:
        return pd.DataFrame(columns=[
            "shortage_id", "sku_id", "location_id", "shortage_week", "shortage_date",
            "shortage_qty", "cumulative_shortage_qty", "unmet_demand_qty",
            "root_cause", "priority_score", "priority_rank", "status", "created_at"
        ])

    deficit_df["shortage_qty"] = deficit_df["projected_balance"].abs()
    deficit_df["unmet_demand_qty"] = np.minimum(deficit_df["demand_qty"], deficit_df["shortage_qty"])
    deficit_df["shortage_week"] = deficit_df["week_str"]

    # Compute cumulative shortage per (sku_id, location_id)
    deficit_df = deficit_df.sort_values(by=["sku_id", "location_id", "week_num"]).reset_index(drop=True)
    deficit_df["cumulative_shortage_qty"] = (
        deficit_df.groupby(["sku_id", "location_id"])["unmet_demand_qty"]
        .cumsum()
        .round(2)
    )

    # Compute priority score:
    # 1. Financial severity = shortage_qty * selling_price
    # 2. Location critical role multiplier
    raw_scores = []
    for _, row in deficit_df.iterrows():
        sku_id = row["sku_id"]
        loc_id = row["location_id"]
        qty = row["shortage_qty"]

        price = sku_price_map.get(sku_id, 50.0)
        loc_weight = loc_type_weights.get(loc_type_map.get(loc_id, ""), 1.0)

        dollar_impact = qty * price
        raw_score = (dollar_impact ** 0.5) * loc_weight
        raw_scores.append(raw_score)

    deficit_df["raw_score"] = raw_scores

    # Normalize priority score to [10.0, 99.0]
    min_score = deficit_df["raw_score"].min()
    max_score = deficit_df["raw_score"].max()
    score_range = max_score - min_score if max_score > min_score else 1.0

    deficit_df["priority_score"] = (
        10.0 + ((deficit_df["raw_score"] - min_score) / score_range) * 89.0
    ).round(2)

    # Rank shortages horizon-wide: 1 = highest priority score
    deficit_df = deficit_df.sort_values(by=["priority_score", "shortage_qty"], ascending=[False, False]).reset_index(drop=True)
    deficit_df["priority_rank"] = np.arange(1, len(deficit_df) + 1)

    # Sort deterministically back by (sku_id, location_id, week_num) for stable IDs
    deficit_df = deficit_df.sort_values(by=["sku_id", "location_id", "week_num"]).reset_index(drop=True)

    shortage_ids = [build_shortage_id(i + 1, year) for i in range(len(deficit_df))]
    deficit_df["shortage_id"] = shortage_ids

    # Date and timestamp formatting
    dates = []
    created_ats = []
    for _, row in deficit_df.iterrows():
        w = int(row["week_num"])
        mon = get_monday_of_week(year, w)
        dates.append(mon)
        created_ats.append(f"{mon}T06:00:00Z")

    deficit_df["shortage_date"] = dates
    deficit_df["created_at"] = created_ats
    deficit_df["status"] = ShortageStatus.OPEN.value

    # Temporary placeholder for root_cause, populated by root_cause module
    deficit_df["root_cause"] = "DEMAND_SPIKE"

    return deficit_df
