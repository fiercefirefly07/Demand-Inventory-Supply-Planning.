"""
Projected Available Balance (PAB) Engine for Oryva Planning.
Computes week-by-week projected inventory balance per SKU-location:
Opening Stock + Inbound (POs + Production) - Demand = Closing Projected Balance.
Reconciles strictly across all 52 planning weeks.
"""

from typing import Dict, List, Tuple
from datetime import date
import pandas as pd
import numpy as np

from oryva_planning.schema.enums import POStatus, ProductionStatus
from oryva_planning.schema.id_builders import parse_week_string


def get_week_number_from_date(dt_str: str) -> Tuple[int, int]:
    """Return (year, week_num) from ISO date string YYYY-MM-DD."""
    dt = date.fromisoformat(dt_str)
    iso_cal = dt.isocalendar()
    return iso_cal.year, iso_cal.week


def compute_projected_available_balance(
    sku_df: pd.DataFrame,
    location_df: pd.DataFrame,
    inventory_df: pd.DataFrame,
    demand_df: pd.DataFrame,
    po_df: pd.DataFrame,
    production_df: pd.DataFrame,
    num_weeks: int,
    year: int = 2026,
) -> pd.DataFrame:
    """
    Compute week-by-week projected balance for each SKU and Location.
    Returns DataFrame containing:
    [sku_id, location_id, week_str, opening_stock, inbound_po_qty, inbound_prod_qty, total_inbound_qty, demand_qty, projected_balance]
    """
    # 1. Opening stock map: (sku_id, location_id) -> initial on_hand_qty
    initial_stock_map = dict(
        zip(
            zip(inventory_df["sku_id"], inventory_df["location_id"]),
            inventory_df["on_hand_qty"]
        )
    )

    # 2. Demand map: (sku_id, location_id, week_str) -> forecast_qty
    demand_map = dict(
        zip(
            zip(demand_df["sku_id"], demand_df["location_id"], demand_df["forecast_week"]),
            demand_df["forecast_qty"]
        )
    )

    # 3. Inbound PO receipts map: (sku_id, location_id, week_str) -> inbound_qty
    # Valid inbound POs: not cancelled. Delivery week based on revised_delivery_date
    valid_pos = po_df[po_df["current_status"] != POStatus.CANCELLED.value].copy()
    valid_pos["deliv_year_week"] = valid_pos["revised_delivery_date"].apply(get_week_number_from_date)
    # Filter to current planning year
    valid_pos = valid_pos[valid_pos["deliv_year_week"].apply(lambda yw: yw[0] == year)].copy()
    valid_pos["deliv_week_str"] = valid_pos["deliv_year_week"].apply(lambda yw: f"{year}W{yw[1]:02d}")

    po_inbound_grouped = (
        valid_pos.groupby(["sku_id", "destination_location_id", "deliv_week_str"])["order_qty"]
        .sum()
        .to_dict()
    )

    # 4. Inbound Production receipts map: (sku_id, location_id, planned_week) -> actual_output_qty or planned_output_qty
    # If completed or in-progress, use actual_output_qty; else planned_output_qty
    valid_prod = production_df[production_df["status"] != ProductionStatus.DELAYED.value].copy()
    valid_prod["effective_output"] = np.where(
        valid_prod["status"] == ProductionStatus.COMPLETED.value,
        valid_prod["actual_output_qty"],
        valid_prod["planned_output_qty"]
    )
    prod_inbound_grouped = (
        valid_prod.groupby(["sku_id", "location_id", "planned_week"])["effective_output"]
        .sum()
        .to_dict()
    )

    sku_ids = sku_df["sku_id"].tolist()
    loc_ids = location_df["location_id"].tolist()

    balance_rows = []

    for sku_id in sku_ids:
        for loc_id in loc_ids:
            current_opening = initial_stock_map.get((sku_id, loc_id), 0.0)

            for w in range(1, num_weeks + 1):
                week_str = f"{year}W{w:02d}"

                inbound_po = po_inbound_grouped.get((sku_id, loc_id, week_str), 0.0)
                inbound_prod = prod_inbound_grouped.get((sku_id, loc_id, week_str), 0.0)
                total_inbound = inbound_po + inbound_prod

                demand = demand_map.get((sku_id, loc_id, week_str), 0.0)

                # Projected Available Balance formula
                closing_balance = round(float(current_opening + total_inbound - demand), 2)

                balance_rows.append({
                    "sku_id": sku_id,
                    "location_id": loc_id,
                    "week_num": w,
                    "week_str": week_str,
                    "opening_stock": round(float(current_opening), 2),
                    "inbound_po_qty": round(float(inbound_po), 2),
                    "inbound_prod_qty": round(float(inbound_prod), 2),
                    "total_inbound_qty": round(float(total_inbound), 2),
                    "demand_qty": round(float(demand), 2),
                    "projected_balance": closing_balance,
                })

                # Carry forward closing balance to next week's opening stock
                # If closing balance is negative, physical stock carried is 0 (or deficit backlog)
                current_opening = max(0.0, closing_balance)

    return pd.DataFrame(balance_rows)
