"""
Synthetic Anomaly Injector for Oryva Planning.
Injects 5 labelled edge cases into an isolated copy of clean baseline data:
1. double_counted_inbound: PO counted twice / duplicate inbound record
2. unapproved_substitute: Substitute SKU flagged with approved = False
3. supplier_capacity_exceeded: PO order quantity strictly exceeds supplier max capacity
4. shortage_without_lead_time: Sourcing lead time set to 0 or ignored
5. uom_mismatch: Discrepancy between record UOM and master SKU UOM

Records every modification in data/ground_truth/ground_truth.csv.
Planning code must NEVER read ground_truth.csv.
"""

from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

from oryva_planning.config import PlanningConfig
from oryva_planning.schema.enums import AnomalyIssueType, UnitOfMeasure


def inject_anomalies(
    datasets: Dict[str, pd.DataFrame],
    config: PlanningConfig,
    save_ground_truth: bool = True,
) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame]:
    """
    Inject labelled anomalies into a deep copy of baseline datasets.
    Returns:
    1. injected_datasets: copy of datasets containing injected edge cases.
    2. ground_truth_df: ground truth labels mapping affected_id to issue_type.
    """
    # Create isolated deep copies so clean baseline is never mutated
    injected = {k: v.copy(deep=True) for k, v in datasets.items()}
    ground_truth_records = []
    anomaly_seq = 1

    cfg_inj = config.anomaly_injection
    if not cfg_inj.enabled:
        return injected, pd.DataFrame(columns=[
            "anomaly_id", "issue_type", "table_name", "affected_id",
            "expected_detection_rule", "details"
        ])

    rng = np.random.default_rng(config.seed + 999)

    # -------------------------------------------------------------------------
    # 1. double_counted_inbound: Inject duplicate PO records
    # -------------------------------------------------------------------------
    n_double = cfg_inj.inbound_double_count_n
    po_df = injected["purchaseorder"]
    if len(po_df) > 0 and n_double > 0:
        chosen_indices = rng.choice(len(po_df), size=min(n_double, len(po_df)), replace=False)
        duplicate_rows = []
        for idx in chosen_indices:
            row = po_df.iloc[idx].to_dict()
            orig_po_id = row["po_id"]
            # Create a clone record with identical core fields but marked clone ID
            clone_po_id = f"PO-2026-9{orig_po_id[-5:]}"
            clone_row = row.copy()
            clone_row["po_id"] = clone_po_id
            duplicate_rows.append(clone_row)

            ground_truth_records.append({
                "anomaly_id": f"ANOM-{anomaly_seq:04d}",
                "issue_type": AnomalyIssueType.DOUBLE_COUNTED_INBOUND.value,
                "table_name": "PurchaseOrder",
                "affected_id": clone_po_id,
                "expected_detection_rule": "Duplicate purchase orders having identical supplier, sku, location, dates, and order_qty",
                "details": f"Cloned PO {clone_po_id} duplicates original {orig_po_id}",
            })
            anomaly_seq += 1

        injected["purchaseorder"] = pd.concat([po_df, pd.DataFrame(duplicate_rows)], ignore_index=True)

    # -------------------------------------------------------------------------
    # 2. unapproved_substitute: Flip approved flag to False on SkuSubstitute
    # -------------------------------------------------------------------------
    n_sub = cfg_inj.unapproved_substitute_n
    sub_df = injected["sku_substitute"]
    if len(sub_df) > 0 and n_sub > 0:
        sub_indices = rng.choice(len(sub_df), size=min(n_sub, len(sub_df)), replace=False)
        for idx in sub_indices:
            sub_id = sub_df.loc[idx, "substitute_id"]
            sub_df.loc[idx, "approved"] = False

            ground_truth_records.append({
                "anomaly_id": f"ANOM-{anomaly_seq:04d}",
                "issue_type": AnomalyIssueType.UNAPPROVED_SUBSTITUTE.value,
                "table_name": "SkuSubstitute",
                "affected_id": sub_id,
                "expected_detection_rule": "Substitute relationship with approved = False",
                "details": f"Substitute {sub_id} marked unapproved (approved=False)",
            })
            anomaly_seq += 1

    # -------------------------------------------------------------------------
    # 3. supplier_capacity_exceeded: Exceed supplier max_weekly_capacity
    # -------------------------------------------------------------------------
    n_cap = cfg_inj.supplier_capacity_exceeded_n
    cap_df = injected["suppliercapacity"]
    po_df = injected["purchaseorder"]
    if len(po_df) > 0 and len(cap_df) > 0 and n_cap > 0:
        po_indices = rng.choice(len(po_df), size=min(n_cap, len(po_df)), replace=False)
        for idx in po_indices:
            po_id = po_df.loc[idx, "po_id"]
            sup_id = po_df.loc[idx, "supplier_id"]
            sku_id = po_df.loc[idx, "sku_id"]

            # Lookup max capacity
            matching_cap = cap_df[(cap_df["supplier_id"] == sup_id) & (cap_df["sku_id"] == sku_id)]
            max_cap = matching_cap["max_weekly_capacity"].max() if len(matching_cap) > 0 else 500.0

            # Exceed capacity by 3.5x
            excess_qty = round(float(max_cap * 3.5), 2)
            po_df.loc[idx, "order_qty"] = excess_qty

            ground_truth_records.append({
                "anomaly_id": f"ANOM-{anomaly_seq:04d}",
                "issue_type": AnomalyIssueType.SUPPLIER_CAPACITY_EXCEEDED.value,
                "table_name": "PurchaseOrder",
                "affected_id": po_id,
                "expected_detection_rule": "PO order_qty exceeds supplier weekly capacity ceiling",
                "details": f"PO {po_id} quantity inflated to {excess_qty} (capacity is {max_cap})",
            })
            anomaly_seq += 1

    # -------------------------------------------------------------------------
    # 4. shortage_without_lead_time: Sourcing lead time set to 0
    # -------------------------------------------------------------------------
    n_lt = cfg_inj.shortage_without_lead_time_n
    lt_df = injected["leadtime"]
    if len(lt_df) > 0 and n_lt > 0:
        lt_indices = rng.choice(len(lt_df), size=min(n_lt, len(lt_df)), replace=False)
        for idx in lt_indices:
            lt_id = lt_df.loc[idx, "lead_time_id"]
            lt_df.loc[idx, "planned_lead_time_days"] = 0

            ground_truth_records.append({
                "anomaly_id": f"ANOM-{anomaly_seq:04d}",
                "issue_type": AnomalyIssueType.SHORTAGE_WITHOUT_LEAD_TIME.value,
                "table_name": "LeadTime",
                "affected_id": lt_id,
                "expected_detection_rule": "Lead time constraint set to 0 days (shortage evaluated without lead time)",
                "details": f"LeadTime record {lt_id} set to planned_lead_time_days = 0",
            })
            anomaly_seq += 1

    # -------------------------------------------------------------------------
    # 5. uom_mismatch: Discrepancy between PO UOM and SKU master UOM
    # -------------------------------------------------------------------------
    n_uom = cfg_inj.uom_mismatch_n
    sku_df = injected["sku"]
    po_df = injected["purchaseorder"]
    if len(po_df) > 0 and n_uom > 0:
        uom_indices = rng.choice(len(po_df), size=min(n_uom, len(po_df)), replace=False)
        # Create a currency/UOM mismatch column or modify currency to an invalid UOM
        for idx in uom_indices:
            po_id = po_df.loc[idx, "po_id"]
            sku_id = po_df.loc[idx, "sku_id"]
            orig_uom = sku_df[sku_df["sku_id"] == sku_id]["unit_of_measure"].iloc[0]

            # Invert UOM: if EA -> PALLET, else EA
            bad_uom = "PALLET" if orig_uom == "EA" else "EA"
            po_df.loc[idx, "currency"] = f"MISMATCH_{bad_uom}"

            ground_truth_records.append({
                "anomaly_id": f"ANOM-{anomaly_seq:04d}",
                "issue_type": AnomalyIssueType.UOM_MISMATCH.value,
                "table_name": "PurchaseOrder",
                "affected_id": po_id,
                "expected_detection_rule": "Purchase order UOM mismatch with parent SKU master UOM",
                "details": f"PO {po_id} has unit measure {bad_uom} vs parent SKU {sku_id} {orig_uom}",
            })
            anomaly_seq += 1

    ground_truth_df = pd.DataFrame(ground_truth_records)

    if save_ground_truth:
        gt_dir = Path(config.paths.ground_truth_dir)
        gt_dir.mkdir(parents=True, exist_ok=True)
        gt_file = gt_dir / "ground_truth.csv"
        ground_truth_df.to_csv(gt_file, index=False, lineterminator="\n")

    return injected, ground_truth_df
