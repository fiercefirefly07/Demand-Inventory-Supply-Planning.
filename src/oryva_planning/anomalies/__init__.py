"""
Synthetic anomaly injectors and detectors for Oryva Planning.
Injects 5 labelled edge cases and writes ground truth independently.
"""

from oryva_planning.anomalies.injectors import inject_anomalies
from oryva_planning.anomalies.detectors import (
    detect_double_counted_inbound,
    detect_unapproved_substitute,
    detect_supplier_capacity_exceeded,
    detect_shortage_without_lead_time,
    detect_uom_mismatch,
    evaluate_anomaly_detection,
)

__all__ = [
    "inject_anomalies",
    "detect_double_counted_inbound",
    "detect_unapproved_substitute",
    "detect_supplier_capacity_exceeded",
    "detect_shortage_without_lead_time",
    "detect_uom_mismatch",
    "evaluate_anomaly_detection",
]
