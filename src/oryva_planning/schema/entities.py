"""
Entity definitions for Oryva Planning.
Defines all 11 core entities, bridge tables, event logs, and evidence records
using Pydantic with strict typing, field validations, PK/FK metadata, and
cardinality definitions.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict

from oryva_planning.schema.enums import (
    UnitOfMeasure,
    SkuLifecycle,
    SkuCategory,
    LocationType,
    SupplierTier,
    InventoryStatus,
    POStatus,
    ProductionStatus,
    ShortageRootCause,
    ShortageStatus,
    MitigationActionType,
    MitigationStatus,
    SourceEntityType,
)
from oryva_planning.schema.id_builders import (
    REGEX_SKU,
    REGEX_LOCATION,
    REGEX_SUPPLIER,
    REGEX_DEMAND,
    REGEX_INVENTORY,
    REGEX_SUPPLIER_CAPACITY,
    REGEX_LEAD_TIME,
    REGEX_PO,
    REGEX_PO_EVENT,
    REGEX_PRODUCTION_PLAN,
    REGEX_SHORTAGE,
    REGEX_MITIGATION,
    REGEX_SKU_SUPPLIER,
    REGEX_SKU_SUBSTITUTE,
    REGEX_SHORTAGE_EVIDENCE,
)


class BaseEntity(BaseModel):
    """Base class for all entities with strict validation and dict export."""
    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
        frozen=True
    )


# ==========================================
# 1. SKU (Master)
# ==========================================
class SKU(BaseEntity):
    sku_id: str = Field(
        ...,
        pattern=REGEX_SKU.pattern,
        description="Primary Key. Zero-padded SKU identifier (SKU-000001).",
        json_schema_extra={"pk": True, "unique": True}
    )
    name: str = Field(..., min_length=1, description="Descriptive SKU item name.")
    category: SkuCategory = Field(..., description="Product category hierarchy.")
    unit_of_measure: UnitOfMeasure = Field(..., description="Standard inventory unit.")
    unit_cost: float = Field(..., ge=0.01, description="Standard cost per unit in USD.")
    selling_price: float = Field(..., ge=0.01, description="Standard selling price per unit in USD.")
    holding_cost_rate: float = Field(..., ge=0.01, le=1.0, description="Annual inventory holding cost fraction (e.g. 0.20 for 20%).")
    lifecycle_status: SkuLifecycle = Field(default=SkuLifecycle.ACTIVE, description="Current lifecycle state.")
    effective_start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Effective start date YYYY-MM-DD.")
    effective_end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Effective end date YYYY-MM-DD.")


# ==========================================
# 2. Location (Master)
# ==========================================
class Location(BaseEntity):
    location_id: str = Field(
        ...,
        pattern=REGEX_LOCATION.pattern,
        description="Primary Key. Zero-padded location identifier (LOC-0001).",
        json_schema_extra={"pk": True, "unique": True}
    )
    name: str = Field(..., min_length=1, description="Facility / warehouse / plant name.")
    type: LocationType = Field(..., description="Facility operational type.")
    region: str = Field(..., min_length=1, description="Geographic distribution region.")
    holding_cost_per_unit_day: float = Field(..., ge=0.0, description="Warehouse storage cost per unit-day in USD.")
    capacity_units: int = Field(..., ge=0, description="Maximum unit storage capacity.")
    is_active: bool = Field(default=True, description="Facility operational status.")
    effective_start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Effective start date YYYY-MM-DD.")
    effective_end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Effective end date YYYY-MM-DD.")


# ==========================================
# 3. Supplier (Master)
# ==========================================
class Supplier(BaseEntity):
    supplier_id: str = Field(
        ...,
        pattern=REGEX_SUPPLIER.pattern,
        description="Primary Key. Zero-padded supplier identifier (SUP-000001).",
        json_schema_extra={"pk": True, "unique": True}
    )
    name: str = Field(..., min_length=1, description="Vendor / supplier commercial name.")
    country: str = Field(..., min_length=2, description="Country of supplier headquarters / manufacturing.")
    reliability_score: float = Field(..., ge=0.0, le=1.0, description="Historical on-time delivery probability (0.0 to 1.0).")
    tier: SupplierTier = Field(..., description="Strategic supplier classification tier.")
    is_active: bool = Field(default=True, description="Vendor contractual active status.")
    effective_start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Effective start date YYYY-MM-DD.")
    effective_end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Effective end date YYYY-MM-DD.")


# ==========================================
# 4. SkuSupplier (Bridge N:M)
# ==========================================
class SkuSupplier(BaseEntity):
    sku_supplier_id: str = Field(
        ...,
        pattern=REGEX_SKU_SUPPLIER.pattern,
        description="Primary Key. Composite identifier (SKUSUP-<sku>-<supplier>).",
        json_schema_extra={"pk": True, "unique": True}
    )
    sku_id: str = Field(..., pattern=REGEX_SKU.pattern, json_schema_extra={"fk": "SKU.sku_id"})
    supplier_id: str = Field(..., pattern=REGEX_SUPPLIER.pattern, json_schema_extra={"fk": "Supplier.supplier_id"})
    is_primary: bool = Field(default=False, description="Whether this is the preferred primary supplier.")
    supplier_part_number: str = Field(..., min_length=1, description="Vendor catalog part identifier.")
    effective_start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    effective_end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")


# ==========================================
# 5. SkuSubstitute (Bridge N:M with approved flag)
# ==========================================
class SkuSubstitute(BaseEntity):
    substitute_id: str = Field(
        ...,
        pattern=REGEX_SKU_SUBSTITUTE.pattern,
        description="Primary Key. Composite substitute identifier (SUB-<sku>-<substitute_sku>).",
        json_schema_extra={"pk": True, "unique": True}
    )
    primary_sku_id: str = Field(..., pattern=REGEX_SKU.pattern, json_schema_extra={"fk": "SKU.sku_id"})
    substitute_sku_id: str = Field(..., pattern=REGEX_SKU.pattern, json_schema_extra={"fk": "SKU.sku_id"})
    conversion_rate: float = Field(default=1.0, gt=0.0, description="Units of substitute required per 1 unit of primary.")
    approved: bool = Field(default=True, description="Formal engineering / quality approval flag.")
    effective_start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    effective_end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")


# ==========================================
# 6. ForecastDemand (Dependent Fact)
# ==========================================
class ForecastDemand(BaseEntity):
    demand_id: str = Field(
        ...,
        pattern=REGEX_DEMAND.pattern,
        description="Primary Key. Deterministic demand ID: DEM-<sku>-<location>-2026W01.",
        json_schema_extra={"pk": True, "unique": True}
    )
    sku_id: str = Field(..., pattern=REGEX_SKU.pattern, json_schema_extra={"fk": "SKU.sku_id"})
    location_id: str = Field(..., pattern=REGEX_LOCATION.pattern, json_schema_extra={"fk": "Location.location_id"})
    forecast_week: str = Field(..., pattern=r"^\d{4}W\d{2}$", description="Planning week in format YYYYWww.")
    forecast_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Monday start date of forecast week.")
    mean_demand: float = Field(..., ge=0.0, description="Underlying unconstrained statistical mean demand.")
    forecast_qty: float = Field(..., ge=0.0, description="Simulated forecast quantity (units).")
    unit_of_measure: UnitOfMeasure = Field(..., description="Unit of measure for demand.")


# ==========================================
# 7. Inventory (Dependent State Fact)
# ==========================================
class Inventory(BaseEntity):
    inventory_id: str = Field(
        ...,
        pattern=REGEX_INVENTORY.pattern,
        description="Primary Key. Identifier: INV-<sku>-<location>.",
        json_schema_extra={"pk": True, "unique": True}
    )
    sku_id: str = Field(..., pattern=REGEX_SKU.pattern, json_schema_extra={"fk": "SKU.sku_id"})
    location_id: str = Field(..., pattern=REGEX_LOCATION.pattern, json_schema_extra={"fk": "Location.location_id"})
    on_hand_qty: float = Field(..., ge=0.0, description="Physical opening inventory on hand.")
    safety_stock_qty: float = Field(..., ge=0.0, description="Buffer target safety stock quantity.")
    reorder_point: float = Field(..., ge=0.0, description="Inventory level that triggers replenishment.")
    unit_of_measure: UnitOfMeasure = Field(..., description="Unit of measure.")
    effective_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Inventory valuation snapshot date.")
    status: InventoryStatus = Field(default=InventoryStatus.AVAILABLE, description="Inventory availability state.")


# ==========================================
# 8. SupplierCapacity (Dependent Constraint)
# ==========================================
class SupplierCapacity(BaseEntity):
    capacity_id: str = Field(
        ...,
        pattern=REGEX_SUPPLIER_CAPACITY.pattern,
        description="Primary Key. Unique capacity slice identifier: CAP-2026-000001.",
        json_schema_extra={"pk": True, "unique": True}
    )
    supplier_id: str = Field(..., pattern=REGEX_SUPPLIER.pattern, json_schema_extra={"fk": "Supplier.supplier_id"})
    sku_id: str = Field(..., pattern=REGEX_SKU.pattern, json_schema_extra={"fk": "SKU.sku_id"})
    period_week: str = Field(..., pattern=r"^\d{4}W\d{2}$", description="Production capacity planning week.")
    max_weekly_capacity: float = Field(..., ge=0.0, description="Total contracted weekly production quota.")
    committed_qty: float = Field(..., ge=0.0, description="Quantity already committed to purchase orders.")
    available_capacity: float = Field(..., ge=0.0, description="Remaining uncommitted capacity (max - committed).")
    effective_start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    effective_end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")


# ==========================================
# 9. LeadTime (Dependent Constraint)
# ==========================================
class LeadTime(BaseEntity):
    lead_time_id: str = Field(
        ...,
        pattern=REGEX_LEAD_TIME.pattern,
        description="Primary Key. Identifier: LT-000001.",
        json_schema_extra={"pk": True, "unique": True}
    )
    supplier_id: str = Field(..., pattern=REGEX_SUPPLIER.pattern, json_schema_extra={"fk": "Supplier.supplier_id"})
    sku_id: str = Field(..., pattern=REGEX_SKU.pattern, json_schema_extra={"fk": "SKU.sku_id"})
    destination_location_id: str = Field(..., pattern=REGEX_LOCATION.pattern, json_schema_extra={"fk": "Location.location_id"})
    planned_lead_time_days: int = Field(..., ge=1, description="Standard supplier order-to-delivery lead time (days).")
    minimum_order_qty: float = Field(..., ge=1.0, description="Minimum order quantity (MOQ).")
    order_multiple_qty: float = Field(..., ge=1.0, description="Packaging lot size multiple.")
    expedited_lead_time_days: int = Field(..., ge=1, description="Air / expedited emergency delivery lead time (days).")
    effective_start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    effective_end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")


# ==========================================
# 10. PurchaseOrder (Transaction Fact)
# ==========================================
class PurchaseOrder(BaseEntity):
    po_id: str = Field(
        ...,
        pattern=REGEX_PO.pattern,
        description="Primary Key. Zero-padded purchase order ID: PO-2026-000001.",
        json_schema_extra={"pk": True, "unique": True}
    )
    supplier_id: str = Field(..., pattern=REGEX_SUPPLIER.pattern, json_schema_extra={"fk": "Supplier.supplier_id"})
    sku_id: str = Field(..., pattern=REGEX_SKU.pattern, json_schema_extra={"fk": "SKU.sku_id"})
    destination_location_id: str = Field(..., pattern=REGEX_LOCATION.pattern, json_schema_extra={"fk": "Location.location_id"})
    order_qty: float = Field(..., ge=1.0, description="Ordered replenishment quantity.")
    unit_cost: float = Field(..., ge=0.01, description="Agreed purchase cost per unit in USD.")
    currency: str = Field(default="USD", description="Currency code ISO 4217.")
    order_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Order release date.")
    promised_delivery_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Supplier acknowledged delivery date.")
    revised_delivery_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Updated estimated delivery date.")
    actual_delivery_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Final receipt date.")
    current_status: POStatus = Field(..., description="Current lifecycle state derived from latest event.")
    created_at: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", description="ISO 8601 audit timestamp.")


# ==========================================
# 11. PurchaseOrderEvent (Audit History Log)
# ==========================================
class PurchaseOrderEvent(BaseEntity):
    event_id: str = Field(
        ...,
        pattern=REGEX_PO_EVENT.pattern,
        description="Primary Key. PO state change event identifier: POE-2026-000001.",
        json_schema_extra={"pk": True, "unique": True}
    )
    po_id: str = Field(..., pattern=REGEX_PO.pattern, json_schema_extra={"fk": "PurchaseOrder.po_id"})
    from_status: Optional[POStatus] = Field(None, description="Previous PO lifecycle state (None if creation).")
    to_status: POStatus = Field(..., description="Transitioned target PO lifecycle state.")
    event_ts: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", description="Timestamp of status change.")
    event_reason: str = Field(..., min_length=1, description="Audit reason for state transition.")
    actor: str = Field(..., min_length=1, description="User role or system triggering transition.")


# ==========================================
# 12. ProductionPlan (Internal Supply Fact)
# ==========================================
class ProductionPlan(BaseEntity):
    plan_id: str = Field(
        ...,
        pattern=REGEX_PRODUCTION_PLAN.pattern,
        description="Primary Key. Production batch run identifier: PROD-2026-000001.",
        json_schema_extra={"pk": True, "unique": True}
    )
    sku_id: str = Field(..., pattern=REGEX_SKU.pattern, json_schema_extra={"fk": "SKU.sku_id"})
    location_id: str = Field(..., pattern=REGEX_LOCATION.pattern, json_schema_extra={"fk": "Location.location_id"})
    planned_week: str = Field(..., pattern=r"^\d{4}W\d{2}$", description="Production execution week.")
    planned_run_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Scheduled production run start date.")
    planned_output_qty: float = Field(..., ge=0.0, description="Scheduled production quantity in units.")
    actual_output_qty: float = Field(..., ge=0.0, description="Completed manufacturing output.")
    status: ProductionStatus = Field(default=ProductionStatus.SCHEDULED, description="Execution status.")
    created_at: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


# ==========================================
# 13. Shortage (Derived Planning Outcome)
# ==========================================
class Shortage(BaseEntity):
    shortage_id: str = Field(
        ...,
        pattern=REGEX_SHORTAGE.pattern,
        description="Primary Key. Identified shortage incident: SHORT-2026-000001.",
        json_schema_extra={"pk": True, "unique": True}
    )
    sku_id: str = Field(..., pattern=REGEX_SKU.pattern, json_schema_extra={"fk": "SKU.sku_id"})
    location_id: str = Field(..., pattern=REGEX_LOCATION.pattern, json_schema_extra={"fk": "Location.location_id"})
    shortage_week: str = Field(..., pattern=r"^\d{4}W\d{2}$", description="Week where balance is negative or below safety stock.")
    shortage_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Date of shortage occurrence.")
    shortage_qty: float = Field(..., ge=0.0, description="Net stock deficit in units below zero.")
    cumulative_shortage_qty: float = Field(..., ge=0.0, description="Cumulative unmet demand across horizon.")
    unmet_demand_qty: float = Field(..., ge=0.0, description="Demand unfulfilled in the specific week.")
    root_cause: ShortageRootCause = Field(..., description="Explainable primary root cause.")
    priority_score: float = Field(..., ge=0.0, le=100.0, description="Prioritization score based on revenue impact and customer SLA.")
    priority_rank: int = Field(..., ge=1, description="Horizon-wide priority rank (1 = highest severity).")
    status: ShortageStatus = Field(default=ShortageStatus.OPEN, description="Resolution lifecycle status.")
    created_at: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


# ==========================================
# 14. ShortageEvidence (Traceability Bridge)
# ==========================================
class ShortageEvidence(BaseEntity):
    evidence_id: str = Field(
        ...,
        pattern=REGEX_SHORTAGE_EVIDENCE.pattern,
        description="Primary Key. Traceability link: EVI-2026-000001.",
        json_schema_extra={"pk": True, "unique": True}
    )
    shortage_id: str = Field(..., pattern=REGEX_SHORTAGE.pattern, json_schema_extra={"fk": "Shortage.shortage_id"})
    source_entity: SourceEntityType = Field(..., description="Source table providing causal evidence.")
    source_id: str = Field(..., min_length=1, description="Primary key of source record.")
    impact_description: str = Field(..., min_length=1, description="Detailed causal narrative.")
    metric_value: float = Field(..., description="Numeric evidence metric (e.g. late days, demand spike %)")


# ==========================================
# 15. MitigationOption (Derived Planning Outcome)
# ==========================================
class MitigationOption(BaseEntity):
    mitigation_id: str = Field(
        ...,
        pattern=REGEX_MITIGATION.pattern,
        description="Primary Key. Mitigation option: MIT-SHORT-2026-000001-01.",
        json_schema_extra={"pk": True, "unique": True}
    )
    shortage_id: str = Field(..., pattern=REGEX_SHORTAGE.pattern, json_schema_extra={"fk": "Shortage.shortage_id"})
    action_type: MitigationActionType = Field(..., description="Mitigation resolution mechanism.")
    substitute_sku_id: Optional[str] = Field(None, pattern=REGEX_SKU.pattern, json_schema_extra={"fk": "SKU.sku_id"})
    expedited_po_id: Optional[str] = Field(None, pattern=REGEX_PO.pattern, json_schema_extra={"fk": "PurchaseOrder.po_id"})
    alt_location_id: Optional[str] = Field(None, pattern=REGEX_LOCATION.pattern, json_schema_extra={"fk": "Location.location_id"})
    cost: float = Field(..., ge=0.0, description="Estimated incremental implementation cost in USD.")
    service_level_impact: float = Field(..., ge=0.0, le=1.0, description="Service level protection ratio (0.0 to 1.0).")
    lead_time_days: int = Field(..., ge=0, description="Days required to activate this mitigation.")
    capacity_check_passed: bool = Field(..., description="True if supplier/logistics capacity is verified.")
    policy_check_passed: bool = Field(..., description="True if business policy rules are satisfied.")
    score: float = Field(..., description="Multi-criteria weighted optimization score.")
    rank: int = Field(..., ge=1, description="Rank among candidate options for this shortage (1 = best).")
    status: MitigationStatus = Field(default=MitigationStatus.PROPOSED, description="Resolution status.")


# Canonical entity registry
CORE_ENTITIES = {
    "SKU": SKU,
    "Location": Location,
    "Supplier": Supplier,
    "SkuSupplier": SkuSupplier,
    "SkuSubstitute": SkuSubstitute,
    "ForecastDemand": ForecastDemand,
    "Inventory": Inventory,
    "SupplierCapacity": SupplierCapacity,
    "LeadTime": LeadTime,
    "PurchaseOrder": PurchaseOrder,
    "PurchaseOrderEvent": PurchaseOrderEvent,
    "ProductionPlan": ProductionPlan,
    "Shortage": Shortage,
    "ShortageEvidence": ShortageEvidence,
    "MitigationOption": MitigationOption,
}

# Table cardinalities and relationships for architectural documentation
ENTITY_RELATIONSHIPS = [
    {"parent": "SKU", "child": "SkuSupplier", "cardinality": "1:N", "type": "Mandatory Bridge"},
    {"parent": "Supplier", "child": "SkuSupplier", "cardinality": "1:N", "type": "Mandatory Bridge"},
    {"parent": "SKU", "child": "SkuSubstitute", "cardinality": "1:N", "type": "Optional Bridge (Substitutes)"},
    {"parent": "SKU", "child": "ForecastDemand", "cardinality": "1:N", "type": "Dependent Demand Fact"},
    {"parent": "Location", "child": "ForecastDemand", "cardinality": "1:N", "type": "Dependent Demand Fact"},
    {"parent": "SKU", "child": "Inventory", "cardinality": "1:1 per Location", "type": "On-hand Stock State"},
    {"parent": "Location", "child": "Inventory", "cardinality": "1:N", "type": "Location Stock State"},
    {"parent": "Supplier", "child": "SupplierCapacity", "cardinality": "1:N", "type": "Weekly Capacity Constraint"},
    {"parent": "SKU", "child": "SupplierCapacity", "cardinality": "1:N", "type": "Weekly Capacity Constraint"},
    {"parent": "Supplier", "child": "LeadTime", "cardinality": "1:N", "type": "Logistics Lead Time Constraint"},
    {"parent": "SKU", "child": "LeadTime", "cardinality": "1:N", "type": "Logistics Lead Time Constraint"},
    {"parent": "Location", "child": "LeadTime", "cardinality": "1:N", "type": "Destination Facility Constraint"},
    {"parent": "Supplier", "child": "PurchaseOrder", "cardinality": "1:N", "type": "Procurement Transaction"},
    {"parent": "SKU", "child": "PurchaseOrder", "cardinality": "1:N", "type": "Procurement Transaction"},
    {"parent": "Location", "child": "PurchaseOrder", "cardinality": "1:N", "type": "Procurement Transaction"},
    {"parent": "PurchaseOrder", "child": "PurchaseOrderEvent", "cardinality": "1:N", "type": "Lifecycle Event History"},
    {"parent": "SKU", "child": "ProductionPlan", "cardinality": "1:N", "type": "Manufacturing Plan"},
    {"parent": "Location", "child": "ProductionPlan", "cardinality": "1:N", "type": "Manufacturing Plan"},
    {"parent": "SKU", "child": "Shortage", "cardinality": "1:N", "type": "Derived Planning Exception"},
    {"parent": "Location", "child": "Shortage", "cardinality": "1:N", "type": "Derived Planning Exception"},
    {"parent": "Shortage", "child": "ShortageEvidence", "cardinality": "1:N", "type": "Causal Traceability Evidence"},
    {"parent": "Shortage", "child": "MitigationOption", "cardinality": "1:N", "type": "Candidate Remediation Options"},
]
