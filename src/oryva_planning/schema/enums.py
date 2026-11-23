"""
Domain enumerations for Oryva Planning.
Single source of truth for all lifecycle states, units of measure, categories,
root causes, and anomaly types.
"""

from enum import Enum


class StrEnum(str, Enum):
    """String-based Enum for serializability and clean display."""
    def __str__(self) -> str:
        return self.value


class UnitOfMeasure(StrEnum):
    EA = "EA"
    BOX = "BOX"
    PALLET = "PALLET"
    KG = "KG"
    L = "L"


class SkuLifecycle(StrEnum):
    ACTIVE = "ACTIVE"
    PHASE_OUT = "PHASE_OUT"
    OBSOLETE = "OBSOLETE"


class SkuCategory(StrEnum):
    RAW_MATERIAL = "RAW_MATERIAL"
    PACKAGING = "PACKAGING"
    SUBASSEMBLY = "SUBASSEMBLY"
    FINISHED_GOOD = "FINISHED_GOOD"


class LocationType(StrEnum):
    MANUFACTURING_PLANT = "MANUFACTURING_PLANT"
    REGIONAL_DC = "REGIONAL_DC"
    CENTRAL_HUB = "CENTRAL_HUB"
    SATELLITE_WH = "SATELLITE_WH"


class SupplierTier(StrEnum):
    TIER_1 = "TIER_1"
    TIER_2 = "TIER_2"
    STRATEGIC = "STRATEGIC"
    COMMODITY = "COMMODITY"


class InventoryStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    QUARANTINE = "QUARANTINE"
    DAMAGED = "DAMAGED"


class POStatus(StrEnum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class ProductionStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    DELAYED = "DELAYED"


class ShortageRootCause(StrEnum):
    DEMAND_SPIKE = "DEMAND_SPIKE"
    LATE_INBOUND = "LATE_INBOUND"
    SUPPLIER_CAPACITY_CONSTRAINT = "SUPPLIER_CAPACITY_CONSTRAINT"
    LEAD_TIME_DELAY = "LEAD_TIME_DELAY"
    QUALITY_HOLD = "QUALITY_HOLD"
    INITIAL_STOCKOUT = "INITIAL_STOCKOUT"


class ShortageStatus(StrEnum):
    OPEN = "OPEN"
    MITIGATED = "MITIGATED"
    UNMITIGATED = "UNMITIGATED"
    IN_REVIEW = "IN_REVIEW"


class MitigationActionType(StrEnum):
    EXPEDITE_PO = "EXPEDITE_PO"
    SUBSTITUTE_SKU = "SUBSTITUTE_SKU"
    TRANSFER_STOCK = "TRANSFER_STOCK"
    INCREASE_PRODUCTION = "INCREASE_PRODUCTION"


class MitigationStatus(StrEnum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"


class AnomalyIssueType(StrEnum):
    DOUBLE_COUNTED_INBOUND = "double_counted_inbound"
    UNAPPROVED_SUBSTITUTE = "unapproved_substitute"
    SUPPLIER_CAPACITY_EXCEEDED = "supplier_capacity_exceeded"
    SHORTAGE_WITHOUT_LEAD_TIME = "shortage_without_lead_time"
    UOM_MISMATCH = "uom_mismatch"


class SourceEntityType(StrEnum):
    FORECAST_DEMAND = "ForecastDemand"
    PURCHASE_ORDER = "PurchaseOrder"
    INVENTORY = "Inventory"
    SUPPLIER_CAPACITY = "SupplierCapacity"
    LEAD_TIME = "LeadTime"
    PRODUCTION_PLAN = "ProductionPlan"
