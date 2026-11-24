"""
Root Cause Diagnostic Engine and Evidence Traceability Bridge for Oryva Planning.
Evaluates supply chain evidence to diagnose root causes:
- DEMAND_SPIKE: Demand exceeds statistical mean (> 1.8x)
- LATE_INBOUND: Inbound PO delivery delayed beyond promised date
- INITIAL_STOCKOUT: Zero stock at beginning of horizon (Week 1-2)
- SUPPLIER_CAPACITY_CONSTRAINT: Capacity capped at contracted limits
- LEAD_TIME_DELAY: Replenishment lead time exceeds available buffer
Populates ShortageEvidence bridge table linking each shortage to source records.
"""

from typing import Tuple, List, Dict
from datetime import date
import pandas as pd
import numpy as np

from oryva_planning.schema.enums import ShortageRootCause, SourceEntityType
from oryva_planning.schema.id_builders import (
    build_shortage_evidence_id,
    build_inventory_id,
    build_demand_id,
)
from oryva_planning.schema.entities import Shortage, ShortageEvidence
from oryva_planning.generators.base import validate_and_sort_dataframe


def diagnose_root_causes_and_evidence(
    shortage_df: pd.DataFrame,
    demand_df: pd.DataFrame,
    inventory_df: pd.DataFrame,
    po_df: pd.DataFrame,
    capacity_df: pd.DataFrame,
    lead_time_df: pd.DataFrame,
    year: int = 2026,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Diagnose explainable root causes and construct ShortageEvidence records.
    Returns:
    1. Updated shortage_df with diagnosed root_cause.
    2. shortage_evidence_df conforming to ShortageEvidence schema.
    """
    if shortage_df.empty:
        empty_evidence = pd.DataFrame(columns=list(ShortageEvidence.model_fields.keys()))
        return shortage_df, empty_evidence

    # Index maps for quick causal lookups
    demand_lookup = {}
    for _, row in demand_df.iterrows():
        key = (row["sku_id"], row["location_id"], row["forecast_week"])
        demand_lookup[key] = (row["demand_id"], row["mean_demand"], row["forecast_qty"])

    inv_lookup = {}
    for _, row in inventory_df.iterrows():
        key = (row["sku_id"], row["location_id"])
        inv_lookup[key] = (row["inventory_id"], row["on_hand_qty"])

    # Map delayed POs by (sku_id, destination_location_id)
    delayed_pos_lookup = {}
    for _, row in po_df.iterrows():
        prom_dt = date.fromisoformat(row["promised_delivery_date"])
        rev_dt = date.fromisoformat(row["revised_delivery_date"])
        delay_days = (rev_dt - prom_dt).days
        if delay_days > 0:
            key = (row["sku_id"], row["destination_location_id"])
            if key not in delayed_pos_lookup:
                delayed_pos_lookup[key] = []
            delayed_pos_lookup[key].append((row["po_id"], delay_days, rev_dt.isoformat()))

    # Map lead time info by (sku_id, destination_location_id)
    lt_lookup = {}
    for _, row in lead_time_df.iterrows():
        key = (row["sku_id"], row["destination_location_id"])
        if key not in lt_lookup:
            lt_lookup[key] = (row["lead_time_id"], row["planned_lead_time_days"])

    # Map supplier capacity by (sku_id, period_week)
    cap_lookup = {}
    for _, row in capacity_df.iterrows():
        key = (row["sku_id"], row["period_week"])
        if key not in cap_lookup:
            cap_lookup[key] = (row["capacity_id"], row["max_weekly_capacity"])

    evidence_rows = []
    evi_seq = 1
    diagnosed_root_causes = []

    for _, s_row in shortage_df.iterrows():
        shortage_id = s_row["shortage_id"]
        sku_id = s_row["sku_id"]
        loc_id = s_row["location_id"]
        week_str = s_row["shortage_week"]
        week_num = int(s_row["week_num"])

        d_key = (sku_id, loc_id, week_str)
        demand_id, mean_demand, forecast_qty = demand_lookup.get(d_key, ("DEM-NA", 50.0, 50.0))

        inv_id, on_hand = inv_lookup.get((sku_id, loc_id), ("INV-NA", 0.0))

        # Diagnostic decision tree
        root_cause = None

        # 1. Early stockout (week 1 or 2 with zero starting inventory)
        if week_num <= 2 and on_hand <= 0.0:
            root_cause = ShortageRootCause.INITIAL_STOCKOUT.value
            eid = build_shortage_evidence_id(evi_seq, year)
            evi_seq += 1
            evidence_rows.append({
                "evidence_id": eid,
                "shortage_id": shortage_id,
                "source_entity": SourceEntityType.INVENTORY.value,
                "source_id": inv_id,
                "impact_description": f"Initial warehouse on-hand stock was depleted ({on_hand} units on-hand) at start of planning horizon",
                "metric_value": float(on_hand),
            })

        # 2. Demand spike (demand > 1.8x baseline mean)
        elif forecast_qty > (1.8 * mean_demand):
            root_cause = ShortageRootCause.DEMAND_SPIKE.value
            spike_ratio = round(forecast_qty / mean_demand, 2)
            eid = build_shortage_evidence_id(evi_seq, year)
            evi_seq += 1
            evidence_rows.append({
                "evidence_id": eid,
                "shortage_id": shortage_id,
                "source_entity": SourceEntityType.FORECAST_DEMAND.value,
                "source_id": demand_id,
                "impact_description": f"Customer demand surged to {forecast_qty} units ({spike_ratio}x historical mean of {mean_demand})",
                "metric_value": float(spike_ratio),
            })

        # 3. Inbound transport delay / Late PO
        elif (sku_id, loc_id) in delayed_pos_lookup:
            po_id, delay_days, rev_dt_str = delayed_pos_lookup[(sku_id, loc_id)][0]
            root_cause = ShortageRootCause.LATE_INBOUND.value
            eid = build_shortage_evidence_id(evi_seq, year)
            evi_seq += 1
            evidence_rows.append({
                "evidence_id": eid,
                "shortage_id": shortage_id,
                "source_entity": SourceEntityType.PURCHASE_ORDER.value,
                "source_id": po_id,
                "impact_description": f"Inbound replenishment shipment delayed by {delay_days} days beyond promised schedule",
                "metric_value": float(delay_days),
            })

        # 4. Supplier capacity ceiling
        elif (sku_id, week_str) in cap_lookup:
            cap_id, max_cap = cap_lookup[(sku_id, week_str)]
            root_cause = ShortageRootCause.SUPPLIER_CAPACITY_CONSTRAINT.value
            eid = build_shortage_evidence_id(evi_seq, year)
            evi_seq += 1
            evidence_rows.append({
                "evidence_id": eid,
                "shortage_id": shortage_id,
                "source_entity": SourceEntityType.SUPPLIER_CAPACITY.value,
                "source_id": cap_id,
                "impact_description": f"Supplier manufacturing output was constrained by contracted weekly ceiling of {max_cap} units",
                "metric_value": float(max_cap),
            })

        # 5. Lead time buffer exhaustion
        else:
            root_cause = ShortageRootCause.LEAD_TIME_DELAY.value
            lt_id, lt_days = lt_lookup.get((sku_id, loc_id), ("LT-NA", 14))
            eid = build_shortage_evidence_id(evi_seq, year)
            evi_seq += 1
            evidence_rows.append({
                "evidence_id": eid,
                "shortage_id": shortage_id,
                "source_entity": SourceEntityType.LEAD_TIME.value,
                "source_id": lt_id,
                "impact_description": f"Replenishment lead time of {lt_days} days exceeded remaining order cycle window",
                "metric_value": float(lt_days),
            })

        diagnosed_root_causes.append(root_cause)

        # Always attach supporting ForecastDemand row as secondary evidence
        eid_demand = build_shortage_evidence_id(evi_seq, year)
        evi_seq += 1
        evidence_rows.append({
            "evidence_id": eid_demand,
            "shortage_id": shortage_id,
            "source_entity": SourceEntityType.FORECAST_DEMAND.value,
            "source_id": demand_id,
            "impact_description": f"Net demand requirement was {forecast_qty} units during shortage week {week_str}",
            "metric_value": float(forecast_qty),
        })

    shortage_df["root_cause"] = diagnosed_root_causes

    # Enforce Pydantic validation on Shortage and ShortageEvidence
    shortage_cols = list(Shortage.model_fields.keys())
    validated_shortage_df = validate_and_sort_dataframe(
        shortage_df[shortage_cols], Shortage, "shortage_id", shortage_cols
    )

    evidence_cols = list(ShortageEvidence.model_fields.keys())
    df_evidence = pd.DataFrame(evidence_rows)
    validated_evidence_df = validate_and_sort_dataframe(
        df_evidence, ShortageEvidence, "evidence_id", evidence_cols
    )

    return validated_shortage_df, validated_evidence_df
