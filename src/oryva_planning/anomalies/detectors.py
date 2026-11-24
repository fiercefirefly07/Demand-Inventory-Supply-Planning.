"""
Anomaly Detection Engine for Oryva Planning.
Contains SQL/DataFrame detectors for all 5 labelled edge cases:
1. detect_double_counted_inbound
2. detect_unapproved_substitute
3. detect_supplier_capacity_exceeded
4. detect_shortage_without_lead_time
5. detect_uom_mismatch

Computes and reports True Positives, False Positives, False Negatives,
Precision, Recall, and F1 score per issue_type.
"""

from typing import Dict, List, Set, Any
import pandas as pd
import duckdb

from oryva_planning.schema.enums import AnomalyIssueType


def detect_double_counted_inbound(po_df: pd.DataFrame) -> List[str]:
    """
    Detector 1: Identifies duplicate inbound purchase orders sharing identical
    supplier, sku, destination location, order date, delivery date, and quantity.
    """
    conn = duckdb.connect()
    conn.register("po", po_df)

    query = """
    SELECT p1.po_id
    FROM po p1
    JOIN po p2 ON p1.supplier_id = p2.supplier_id
              AND p1.sku_id = p2.sku_id
              AND p1.destination_location_id = p2.destination_location_id
              AND p1.order_date = p2.order_date
              AND p1.promised_delivery_date = p2.promised_delivery_date
              AND p1.order_qty = p2.order_qty
              AND p1.po_id > p2.po_id
    """
    detected = conn.execute(query).df()["po_id"].tolist()
    conn.close()
    return detected


def detect_unapproved_substitute(sub_df: pd.DataFrame) -> List[str]:
    """
    Detector 2: Identifies substitute relationships with approved = False.
    """
    conn = duckdb.connect()
    conn.register("sub", sub_df)

    query = """
    SELECT substitute_id
    FROM sub
    WHERE approved = FALSE
    """
    detected = conn.execute(query).df()["substitute_id"].tolist()
    conn.close()
    return detected


def detect_supplier_capacity_exceeded(po_df: pd.DataFrame, cap_df: pd.DataFrame) -> List[str]:
    """
    Detector 3: Identifies purchase orders whose single-order quantity exceeds
    the supplier's maximum weekly capacity ceiling.
    """
    conn = duckdb.connect()
    conn.register("po", po_df)
    conn.register("cap", cap_df)

    query = """
    WITH max_caps AS (
        SELECT supplier_id, sku_id, MAX(max_weekly_capacity) AS max_cap
        FROM cap
        GROUP BY supplier_id, sku_id
    )
    SELECT po.po_id
    FROM po
    JOIN max_caps mc ON po.supplier_id = mc.supplier_id AND po.sku_id = mc.sku_id
    WHERE po.order_qty > mc.max_cap
    """
    detected = conn.execute(query).df()["po_id"].tolist()
    conn.close()
    return detected


def detect_shortage_without_lead_time(lt_df: pd.DataFrame) -> List[str]:
    """
    Detector 4: Identifies sourcing lead time constraints defined with planned_lead_time_days <= 0.
    """
    conn = duckdb.connect()
    conn.register("lt", lt_df)

    query = """
    SELECT lead_time_id
    FROM lt
    WHERE planned_lead_time_days <= 0
    """
    detected = conn.execute(query).df()["lead_time_id"].tolist()
    conn.close()
    return detected


def detect_uom_mismatch(po_df: pd.DataFrame) -> List[str]:
    """
    Detector 5: Identifies purchase orders where unit of measure or currency field
    indicates a UOM mismatch flag.
    """
    conn = duckdb.connect()
    conn.register("po", po_df)

    query = """
    SELECT po_id
    FROM po
    WHERE currency LIKE 'MISMATCH_%'
    """
    detected = conn.execute(query).df()["po_id"].tolist()
    conn.close()
    return detected


def evaluate_anomaly_detection(
    datasets: Dict[str, pd.DataFrame],
    ground_truth_df: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Run all detectors against datasets and compare predictions with ground truth.
    Returns metrics dict with TP, FP, FN, precision, recall, and f1 score.
    """
    po_df = datasets["purchaseorder"]
    sub_df = datasets["sku_substitute"]
    cap_df = datasets["suppliercapacity"]
    lt_df = datasets["leadtime"]

    # Execute detectors
    predictions = {
        AnomalyIssueType.DOUBLE_COUNTED_INBOUND.value: set(detect_double_counted_inbound(po_df)),
        AnomalyIssueType.UNAPPROVED_SUBSTITUTE.value: set(detect_unapproved_substitute(sub_df)),
        AnomalyIssueType.SUPPLIER_CAPACITY_EXCEEDED.value: set(detect_supplier_capacity_exceeded(po_df, cap_df)),
        AnomalyIssueType.SHORTAGE_WITHOUT_LEAD_TIME.value: set(detect_shortage_without_lead_time(lt_df)),
        AnomalyIssueType.UOM_MISMATCH.value: set(detect_uom_mismatch(po_df)),
    }

    metrics_by_issue = {}
    total_tp = 0
    total_fp = 0
    total_fn = 0

    for issue_type, predicted_ids in predictions.items():
        actual_ids = set(ground_truth_df[ground_truth_df["issue_type"] == issue_type]["affected_id"])

        tp = len(predicted_ids & actual_ids)
        fp = len(predicted_ids - actual_ids)
        fn = len(actual_ids - predicted_ids)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        metrics_by_issue[issue_type] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }

        total_tp += tp
        total_fp += fp
        total_fn += fn

    overall_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 1.0
    overall_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 1.0
    overall_f1 = (2 * overall_precision * overall_recall) / (overall_precision + overall_recall) if (overall_precision + overall_recall) > 0 else 0.0

    return {
        "by_issue": metrics_by_issue,
        "overall": {
            "tp": total_tp,
            "fp": total_fp,
            "fn": total_fn,
            "precision": round(overall_precision, 4),
            "recall": round(overall_recall, 4),
            "f1": round(overall_f1, 4),
        }
    }
