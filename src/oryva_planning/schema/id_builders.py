"""
Deterministic ID builders and validators for Oryva Planning.
Enforces zero-padded, immutable, and consistent naming across all entities.
"""

import re
from typing import Tuple

# Regex Patterns for Entity Primary Keys
REGEX_SKU = re.compile(r"^SKU-\d{6}$")
REGEX_LOCATION = re.compile(r"^LOC-\d{4}$")
REGEX_SUPPLIER = re.compile(r"^SUP-\d{6}$")
REGEX_DEMAND = re.compile(r"^DEM-SKU-\d{6}-LOC-\d{4}-\d{4}W\d{2}$")
REGEX_INVENTORY = re.compile(r"^INV-SKU-\d{6}-LOC-\d{4}$")
REGEX_SUPPLIER_CAPACITY = re.compile(r"^CAP-\d{4}-\d{6}$")
REGEX_LEAD_TIME = re.compile(r"^LT-\d{6}$")
REGEX_PO = re.compile(r"^PO-\d{4}-\d{6}$")
REGEX_PO_EVENT = re.compile(r"^POE-\d{4}-\d{6}$")
REGEX_PRODUCTION_PLAN = re.compile(r"^PROD-\d{4}-\d{6}$")
REGEX_SHORTAGE = re.compile(r"^SHORT-\d{4}-\d{6}$")
REGEX_MITIGATION = re.compile(r"^MIT-SHORT-\d{4}-\d{6}-\d{2}$")
REGEX_SKU_SUPPLIER = re.compile(r"^SKUSUP-SKU-\d{6}-SUP-\d{6}$")
REGEX_SKU_SUBSTITUTE = re.compile(r"^SUB-SKU-\d{6}-SKU-\d{6}$")
REGEX_SHORTAGE_EVIDENCE = re.compile(r"^EVI-\d{4}-\d{6}$")


def build_sku_id(seq: int) -> str:
    """Generate SKU identifier (e.g. SKU-000001)."""
    return f"SKU-{seq:06d}"


def build_location_id(seq: int) -> str:
    """Generate Location identifier (e.g. LOC-0001)."""
    return f"LOC-{seq:04d}"


def build_supplier_id(seq: int) -> str:
    """Generate Supplier identifier (e.g. SUP-000001)."""
    return f"SUP-{seq:06d}"


def build_demand_id(sku_id: str, location_id: str, year: int, week: int) -> str:
    """Generate ForecastDemand identifier (e.g. DEM-SKU-000001-LOC-0001-2026W01)."""
    return f"DEM-{sku_id}-{location_id}-{year}W{week:02d}"


def build_inventory_id(sku_id: str, location_id: str) -> str:
    """Generate Inventory identifier (e.g. INV-SKU-000001-LOC-0001)."""
    return f"INV-{sku_id}-{location_id}"


def build_supplier_capacity_id(seq: int, year: int = 2026) -> str:
    """Generate SupplierCapacity identifier (e.g. CAP-2026-000001)."""
    return f"CAP-{year}-{seq:06d}"


def build_lead_time_id(seq: int) -> str:
    """Generate LeadTime identifier (e.g. LT-000001)."""
    return f"LT-{seq:06d}"


def build_po_id(seq: int, year: int = 2026) -> str:
    """Generate PurchaseOrder identifier (e.g. PO-2026-000001)."""
    return f"PO-{year}-{seq:06d}"


def build_po_event_id(seq: int, year: int = 2026) -> str:
    """Generate PurchaseOrderEvent identifier (e.g. POE-2026-000001)."""
    return f"POE-{year}-{seq:06d}"


def build_production_plan_id(seq: int, year: int = 2026) -> str:
    """Generate ProductionPlan identifier (e.g. PROD-2026-000001)."""
    return f"PROD-{year}-{seq:06d}"


def build_shortage_id(seq: int, year: int = 2026) -> str:
    """Generate Shortage identifier (e.g. SHORT-2026-000001)."""
    return f"SHORT-{year}-{seq:06d}"


def build_mitigation_id(shortage_id: str, option_seq: int) -> str:
    """Generate MitigationOption identifier (e.g. MIT-SHORT-2026-000001-01)."""
    return f"MIT-{shortage_id}-{option_seq:02d}"


def build_sku_supplier_id(sku_id: str, supplier_id: str) -> str:
    """Generate SkuSupplier bridge identifier (e.g. SKUSUP-SKU-000001-SUP-000001)."""
    return f"SKUSUP-{sku_id}-{supplier_id}"


def build_sku_substitute_id(primary_sku_id: str, substitute_sku_id: str) -> str:
    """Generate SkuSubstitute bridge identifier (e.g. SUB-SKU-000001-SKU-000002)."""
    return f"SUB-{primary_sku_id}-{substitute_sku_id}"


def build_shortage_evidence_id(seq: int, year: int = 2026) -> str:
    """Generate ShortageEvidence identifier (e.g. EVI-2026-000001)."""
    return f"EVI-{year}-{seq:06d}"


def parse_week_string(week_str: str) -> Tuple[int, int]:
    """Parse '2026W01' into (year: 2026, week: 1)."""
    match = re.match(r"^(\d{4})W(\d{2})$", week_str)
    if not match:
        raise ValueError(f"Invalid week string format: '{week_str}', expected 'YYYYWww'")
    return int(match.group(1)), int(match.group(2))
