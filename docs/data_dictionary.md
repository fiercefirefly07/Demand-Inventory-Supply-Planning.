# Oryva AI - Comprehensive Data Dictionary

This data dictionary is derived directly from the single-source-of-truth Pydantic schema layer in `oryva_planning.schema.entities`.

## Table of Contents

- [SKU](#sku)
- [Location](#location)
- [Supplier](#supplier)
- [SkuSupplier](#skusupplier)
- [SkuSubstitute](#skusubstitute)
- [ForecastDemand](#forecastdemand)
- [Inventory](#inventory)
- [SupplierCapacity](#suppliercapacity)
- [LeadTime](#leadtime)
- [PurchaseOrder](#purchaseorder)
- [PurchaseOrderEvent](#purchaseorderevent)
- [ProductionPlan](#productionplan)
- [Shortage](#shortage)
- [ShortageEvidence](#shortageevidence)
- [MitigationOption](#mitigationoption)

## Entity Relationship Summary

| Parent Entity | Child Entity | Cardinality | Relationship Role |
|---|---|---|---|
| `SKU` | `SkuSupplier` | 1:N | Mandatory Bridge |
| `Supplier` | `SkuSupplier` | 1:N | Mandatory Bridge |
| `SKU` | `SkuSubstitute` | 1:N | Optional Bridge (Substitutes) |
| `SKU` | `ForecastDemand` | 1:N | Dependent Demand Fact |
| `Location` | `ForecastDemand` | 1:N | Dependent Demand Fact |
| `SKU` | `Inventory` | 1:1 per Location | On-hand Stock State |
| `Location` | `Inventory` | 1:N | Location Stock State |
| `Supplier` | `SupplierCapacity` | 1:N | Weekly Capacity Constraint |
| `SKU` | `SupplierCapacity` | 1:N | Weekly Capacity Constraint |
| `Supplier` | `LeadTime` | 1:N | Logistics Lead Time Constraint |
| `SKU` | `LeadTime` | 1:N | Logistics Lead Time Constraint |
| `Location` | `LeadTime` | 1:N | Destination Facility Constraint |
| `Supplier` | `PurchaseOrder` | 1:N | Procurement Transaction |
| `SKU` | `PurchaseOrder` | 1:N | Procurement Transaction |
| `Location` | `PurchaseOrder` | 1:N | Procurement Transaction |
| `PurchaseOrder` | `PurchaseOrderEvent` | 1:N | Lifecycle Event History |
| `SKU` | `ProductionPlan` | 1:N | Manufacturing Plan |
| `Location` | `ProductionPlan` | 1:N | Manufacturing Plan |
| `SKU` | `Shortage` | 1:N | Derived Planning Exception |
| `Location` | `Shortage` | 1:N | Derived Planning Exception |
| `Shortage` | `ShortageEvidence` | 1:N | Causal Traceability Evidence |
| `Shortage` | `MitigationOption` | 1:N | Candidate Remediation Options |

---

### SKU

| Field Name | Type | Status | Units | Uniqueness | Allowed Values | Validation Rules & Description |
|---|---|---|---|---|---|---|
| `sku_id` | `str` | Required | N/A | Unique | `Any valid type` | **Rule:** PRIMARY KEY; UNIQUE; NOT NULL; regex: `^SKU-\d{6}$`<br>**Desc:** Primary Key. Zero-padded SKU identifier (SKU-000001). |
| `name` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** NOT NULL<br>**Desc:** Descriptive SKU item name. |
| `category` | `SkuCategory` | Required | N/A | Non-Unique | `RAW_MATERIAL, PACKAGING, SUBASSEMBLY, FINISHED_GOOD` | **Rule:** NOT NULL<br>**Desc:** Product category hierarchy. |
| `unit_of_measure` | `UnitOfMeasure` | Required | N/A | Non-Unique | `EA, BOX, PALLET, KG, L` | **Rule:** NOT NULL<br>**Desc:** Standard inventory unit. |
| `unit_cost` | `float` | Required | USD | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 0.01<br>**Desc:** Standard cost per unit in USD. |
| `selling_price` | `float` | Required | USD | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 0.01<br>**Desc:** Standard selling price per unit in USD. |
| `holding_cost_rate` | `float` | Required | USD | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 0.01; value <= 1.0<br>**Desc:** Annual inventory holding cost fraction (e.g. 0.20 for 20%). |
| `lifecycle_status` | `SkuLifecycle` | Optional | N/A | Non-Unique | `ACTIVE, PHASE_OUT, OBSOLETE` | **Rule:** NULLABLE<br>**Desc:** Current lifecycle state. |
| `effective_start_date` | `str` | Required | Date (YYYY-MM-DD) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}$`<br>**Desc:** Effective start date YYYY-MM-DD. |
| `effective_end_date` | `str` | Required | Date (YYYY-MM-DD) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}$`<br>**Desc:** Effective end date YYYY-MM-DD. |

### Location

| Field Name | Type | Status | Units | Uniqueness | Allowed Values | Validation Rules & Description |
|---|---|---|---|---|---|---|
| `location_id` | `str` | Required | N/A | Unique | `Any valid type` | **Rule:** PRIMARY KEY; UNIQUE; NOT NULL; regex: `^LOC-\d{4}$`<br>**Desc:** Primary Key. Zero-padded location identifier (LOC-0001). |
| `name` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** NOT NULL<br>**Desc:** Facility / warehouse / plant name. |
| `type` | `LocationType` | Required | N/A | Non-Unique | `MANUFACTURING_PLANT, REGIONAL_DC, CENTRAL_HUB, SATELLITE_WH` | **Rule:** NOT NULL<br>**Desc:** Facility operational type. |
| `region` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** NOT NULL<br>**Desc:** Geographic distribution region. |
| `holding_cost_per_unit_day` | `float` | Required | USD | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 0.0<br>**Desc:** Warehouse storage cost per unit-day in USD. |
| `capacity_units` | `int` | Required | Units / Pieces | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 0<br>**Desc:** Maximum unit storage capacity. |
| `is_active` | `bool` | Optional | N/A | Non-Unique | `True, False` | **Rule:** NULLABLE<br>**Desc:** Facility operational status. |
| `effective_start_date` | `str` | Required | Date (YYYY-MM-DD) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}$`<br>**Desc:** Effective start date YYYY-MM-DD. |
| `effective_end_date` | `str` | Required | Date (YYYY-MM-DD) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}$`<br>**Desc:** Effective end date YYYY-MM-DD. |

### Supplier

| Field Name | Type | Status | Units | Uniqueness | Allowed Values | Validation Rules & Description |
|---|---|---|---|---|---|---|
| `supplier_id` | `str` | Required | N/A | Unique | `Any valid type` | **Rule:** PRIMARY KEY; UNIQUE; NOT NULL; regex: `^SUP-\d{6}$`<br>**Desc:** Primary Key. Zero-padded supplier identifier (SUP-000001). |
| `name` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** NOT NULL<br>**Desc:** Vendor / supplier commercial name. |
| `country` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** NOT NULL<br>**Desc:** Country of supplier headquarters / manufacturing. |
| `reliability_score` | `float` | Required | Ratio / Score (0-1 or 0-100) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 0.0; value <= 1.0<br>**Desc:** Historical on-time delivery probability (0.0 to 1.0). |
| `tier` | `SupplierTier` | Required | N/A | Non-Unique | `TIER_1, TIER_2, STRATEGIC, COMMODITY` | **Rule:** NOT NULL<br>**Desc:** Strategic supplier classification tier. |
| `is_active` | `bool` | Optional | N/A | Non-Unique | `True, False` | **Rule:** NULLABLE<br>**Desc:** Vendor contractual active status. |
| `effective_start_date` | `str` | Required | Date (YYYY-MM-DD) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}$`<br>**Desc:** Effective start date YYYY-MM-DD. |
| `effective_end_date` | `str` | Required | Date (YYYY-MM-DD) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}$`<br>**Desc:** Effective end date YYYY-MM-DD. |

### SkuSupplier

| Field Name | Type | Status | Units | Uniqueness | Allowed Values | Validation Rules & Description |
|---|---|---|---|---|---|---|
| `sku_supplier_id` | `str` | Required | N/A | Unique | `Any valid type` | **Rule:** PRIMARY KEY; UNIQUE; NOT NULL; regex: `^SKUSUP-SKU-\d{6}-SUP-\d{6}$`<br>**Desc:** Primary Key. Composite identifier (SKUSUP-<sku>-<supplier>). |
| `sku_id` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> SKU.sku_id; NOT NULL; regex: `^SKU-\d{6}$`<br>**Desc:**  |
| `supplier_id` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> Supplier.supplier_id; NOT NULL; regex: `^SUP-\d{6}$`<br>**Desc:**  |
| `is_primary` | `bool` | Optional | N/A | Non-Unique | `True, False` | **Rule:** NULLABLE<br>**Desc:** Whether this is the preferred primary supplier. |
| `supplier_part_number` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** NOT NULL<br>**Desc:** Vendor catalog part identifier. |
| `effective_start_date` | `str` | Required | Date (YYYY-MM-DD) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}$`<br>**Desc:**  |
| `effective_end_date` | `str` | Required | Date (YYYY-MM-DD) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}$`<br>**Desc:**  |

### SkuSubstitute

| Field Name | Type | Status | Units | Uniqueness | Allowed Values | Validation Rules & Description |
|---|---|---|---|---|---|---|
| `substitute_id` | `str` | Required | N/A | Unique | `Any valid type` | **Rule:** PRIMARY KEY; UNIQUE; NOT NULL; regex: `^SUB-SKU-\d{6}-SKU-\d{6}$`<br>**Desc:** Primary Key. Composite substitute identifier (SUB-<sku>-<substitute_sku>). |
| `primary_sku_id` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> SKU.sku_id; NOT NULL; regex: `^SKU-\d{6}$`<br>**Desc:**  |
| `substitute_sku_id` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> SKU.sku_id; NOT NULL; regex: `^SKU-\d{6}$`<br>**Desc:**  |
| `conversion_rate` | `float` | Optional | Ratio / Score (0-1 or 0-100) | Non-Unique | `Any valid type` | **Rule:** NULLABLE; value > 0.0<br>**Desc:** Units of substitute required per 1 unit of primary. |
| `approved` | `bool` | Optional | N/A | Non-Unique | `True, False` | **Rule:** NULLABLE<br>**Desc:** Formal engineering / quality approval flag. |
| `effective_start_date` | `str` | Required | Date (YYYY-MM-DD) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}$`<br>**Desc:**  |
| `effective_end_date` | `str` | Required | Date (YYYY-MM-DD) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}$`<br>**Desc:**  |

### ForecastDemand

| Field Name | Type | Status | Units | Uniqueness | Allowed Values | Validation Rules & Description |
|---|---|---|---|---|---|---|
| `demand_id` | `str` | Required | N/A | Unique | `Any valid type` | **Rule:** PRIMARY KEY; UNIQUE; NOT NULL; regex: `^DEM-SKU-\d{6}-LOC-\d{4}-\d{4}W\d{2}$`<br>**Desc:** Primary Key. Deterministic demand ID: DEM-<sku>-<location>-2026W01. |
| `sku_id` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> SKU.sku_id; NOT NULL; regex: `^SKU-\d{6}$`<br>**Desc:**  |
| `location_id` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> Location.location_id; NOT NULL; regex: `^LOC-\d{4}$`<br>**Desc:**  |
| `forecast_week` | `str` | Required | Week (YYYYWww) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}W\d{2}$`<br>**Desc:** Planning week in format YYYYWww. |
| `forecast_date` | `str` | Required | Date (YYYY-MM-DD) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}$`<br>**Desc:** Monday start date of forecast week. |
| `mean_demand` | `float` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 0.0<br>**Desc:** Underlying unconstrained statistical mean demand. |
| `forecast_qty` | `float` | Required | Units / Pieces | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 0.0<br>**Desc:** Simulated forecast quantity (units). |
| `unit_of_measure` | `UnitOfMeasure` | Required | N/A | Non-Unique | `EA, BOX, PALLET, KG, L` | **Rule:** NOT NULL<br>**Desc:** Unit of measure for demand. |

### Inventory

| Field Name | Type | Status | Units | Uniqueness | Allowed Values | Validation Rules & Description |
|---|---|---|---|---|---|---|
| `inventory_id` | `str` | Required | N/A | Unique | `Any valid type` | **Rule:** PRIMARY KEY; UNIQUE; NOT NULL; regex: `^INV-SKU-\d{6}-LOC-\d{4}$`<br>**Desc:** Primary Key. Identifier: INV-<sku>-<location>. |
| `sku_id` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> SKU.sku_id; NOT NULL; regex: `^SKU-\d{6}$`<br>**Desc:**  |
| `location_id` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> Location.location_id; NOT NULL; regex: `^LOC-\d{4}$`<br>**Desc:**  |
| `on_hand_qty` | `float` | Required | Units / Pieces | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 0.0<br>**Desc:** Physical opening inventory on hand. |
| `safety_stock_qty` | `float` | Required | Units / Pieces | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 0.0<br>**Desc:** Buffer target safety stock quantity. |
| `reorder_point` | `float` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 0.0<br>**Desc:** Inventory level that triggers replenishment. |
| `unit_of_measure` | `UnitOfMeasure` | Required | N/A | Non-Unique | `EA, BOX, PALLET, KG, L` | **Rule:** NOT NULL<br>**Desc:** Unit of measure. |
| `effective_date` | `str` | Required | Date (YYYY-MM-DD) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}$`<br>**Desc:** Inventory valuation snapshot date. |
| `status` | `InventoryStatus` | Optional | N/A | Non-Unique | `AVAILABLE, RESERVED, QUARANTINE, DAMAGED` | **Rule:** NULLABLE<br>**Desc:** Inventory availability state. |

### SupplierCapacity

| Field Name | Type | Status | Units | Uniqueness | Allowed Values | Validation Rules & Description |
|---|---|---|---|---|---|---|
| `capacity_id` | `str` | Required | Units / Pieces | Unique | `Any valid type` | **Rule:** PRIMARY KEY; UNIQUE; NOT NULL; regex: `^CAP-\d{4}-\d{6}$`<br>**Desc:** Primary Key. Unique capacity slice identifier: CAP-2026-000001. |
| `supplier_id` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> Supplier.supplier_id; NOT NULL; regex: `^SUP-\d{6}$`<br>**Desc:**  |
| `sku_id` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> SKU.sku_id; NOT NULL; regex: `^SKU-\d{6}$`<br>**Desc:**  |
| `period_week` | `str` | Required | Week (YYYYWww) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}W\d{2}$`<br>**Desc:** Production capacity planning week. |
| `max_weekly_capacity` | `float` | Required | Units / Pieces | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 0.0<br>**Desc:** Total contracted weekly production quota. |
| `committed_qty` | `float` | Required | Units / Pieces | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 0.0<br>**Desc:** Quantity already committed to purchase orders. |
| `available_capacity` | `float` | Required | Units / Pieces | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 0.0<br>**Desc:** Remaining uncommitted capacity (max - committed). |
| `effective_start_date` | `str` | Required | Date (YYYY-MM-DD) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}$`<br>**Desc:**  |
| `effective_end_date` | `str` | Required | Date (YYYY-MM-DD) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}$`<br>**Desc:**  |

### LeadTime

| Field Name | Type | Status | Units | Uniqueness | Allowed Values | Validation Rules & Description |
|---|---|---|---|---|---|---|
| `lead_time_id` | `str` | Required | N/A | Unique | `Any valid type` | **Rule:** PRIMARY KEY; UNIQUE; NOT NULL; regex: `^LT-\d{6}$`<br>**Desc:** Primary Key. Identifier: LT-000001. |
| `supplier_id` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> Supplier.supplier_id; NOT NULL; regex: `^SUP-\d{6}$`<br>**Desc:**  |
| `sku_id` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> SKU.sku_id; NOT NULL; regex: `^SKU-\d{6}$`<br>**Desc:**  |
| `destination_location_id` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> Location.location_id; NOT NULL; regex: `^LOC-\d{4}$`<br>**Desc:**  |
| `planned_lead_time_days` | `int` | Required | Days | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 1<br>**Desc:** Standard supplier order-to-delivery lead time (days). |
| `minimum_order_qty` | `float` | Required | Units / Pieces | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 1.0<br>**Desc:** Minimum order quantity (MOQ). |
| `order_multiple_qty` | `float` | Required | Units / Pieces | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 1.0<br>**Desc:** Packaging lot size multiple. |
| `expedited_lead_time_days` | `int` | Required | Days | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 1<br>**Desc:** Air / expedited emergency delivery lead time (days). |
| `effective_start_date` | `str` | Required | Date (YYYY-MM-DD) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}$`<br>**Desc:**  |
| `effective_end_date` | `str` | Required | Date (YYYY-MM-DD) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}$`<br>**Desc:**  |

### PurchaseOrder

| Field Name | Type | Status | Units | Uniqueness | Allowed Values | Validation Rules & Description |
|---|---|---|---|---|---|---|
| `po_id` | `str` | Required | N/A | Unique | `Any valid type` | **Rule:** PRIMARY KEY; UNIQUE; NOT NULL; regex: `^PO-\d{4}-\d{6}$`<br>**Desc:** Primary Key. Zero-padded purchase order ID: PO-2026-000001. |
| `supplier_id` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> Supplier.supplier_id; NOT NULL; regex: `^SUP-\d{6}$`<br>**Desc:**  |
| `sku_id` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> SKU.sku_id; NOT NULL; regex: `^SKU-\d{6}$`<br>**Desc:**  |
| `destination_location_id` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> Location.location_id; NOT NULL; regex: `^LOC-\d{4}$`<br>**Desc:**  |
| `order_qty` | `float` | Required | Units / Pieces | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 1.0<br>**Desc:** Ordered replenishment quantity. |
| `unit_cost` | `float` | Required | USD | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 0.01<br>**Desc:** Agreed purchase cost per unit in USD. |
| `currency` | `str` | Optional | N/A | Non-Unique | `Any valid type` | **Rule:** NULLABLE<br>**Desc:** Currency code ISO 4217. |
| `order_date` | `str` | Required | Date (YYYY-MM-DD) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}$`<br>**Desc:** Order release date. |
| `promised_delivery_date` | `str` | Required | Date (YYYY-MM-DD) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}$`<br>**Desc:** Supplier acknowledged delivery date. |
| `revised_delivery_date` | `str` | Required | Date (YYYY-MM-DD) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}$`<br>**Desc:** Updated estimated delivery date. |
| `actual_delivery_date` | `Optional` | Optional | Date (YYYY-MM-DD) | Non-Unique | `Any valid type` | **Rule:** NULLABLE; regex: `^\d{4}-\d{2}-\d{2}$`<br>**Desc:** Final receipt date. |
| `current_status` | `POStatus` | Required | N/A | Non-Unique | `DRAFT, CONFIRMED, IN_TRANSIT, DELIVERED, CANCELLED` | **Rule:** NOT NULL<br>**Desc:** Current lifecycle state derived from latest event. |
| `created_at` | `str` | Required | Timestamp ISO-8601 | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$`<br>**Desc:** ISO 8601 audit timestamp. |

### PurchaseOrderEvent

| Field Name | Type | Status | Units | Uniqueness | Allowed Values | Validation Rules & Description |
|---|---|---|---|---|---|---|
| `event_id` | `str` | Required | N/A | Unique | `Any valid type` | **Rule:** PRIMARY KEY; UNIQUE; NOT NULL; regex: `^POE-\d{4}-\d{6}$`<br>**Desc:** Primary Key. PO state change event identifier: POE-2026-000001. |
| `po_id` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> PurchaseOrder.po_id; NOT NULL; regex: `^PO-\d{4}-\d{6}$`<br>**Desc:**  |
| `from_status` | `Optional` | Optional | N/A | Non-Unique | `Any valid type` | **Rule:** NULLABLE<br>**Desc:** Previous PO lifecycle state (None if creation). |
| `to_status` | `POStatus` | Required | N/A | Non-Unique | `DRAFT, CONFIRMED, IN_TRANSIT, DELIVERED, CANCELLED` | **Rule:** NOT NULL<br>**Desc:** Transitioned target PO lifecycle state. |
| `event_ts` | `str` | Required | Timestamp ISO-8601 | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$`<br>**Desc:** Timestamp of status change. |
| `event_reason` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** NOT NULL<br>**Desc:** Audit reason for state transition. |
| `actor` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** NOT NULL<br>**Desc:** User role or system triggering transition. |

### ProductionPlan

| Field Name | Type | Status | Units | Uniqueness | Allowed Values | Validation Rules & Description |
|---|---|---|---|---|---|---|
| `plan_id` | `str` | Required | N/A | Unique | `Any valid type` | **Rule:** PRIMARY KEY; UNIQUE; NOT NULL; regex: `^PROD-\d{4}-\d{6}$`<br>**Desc:** Primary Key. Production batch run identifier: PROD-2026-000001. |
| `sku_id` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> SKU.sku_id; NOT NULL; regex: `^SKU-\d{6}$`<br>**Desc:**  |
| `location_id` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> Location.location_id; NOT NULL; regex: `^LOC-\d{4}$`<br>**Desc:**  |
| `planned_week` | `str` | Required | Week (YYYYWww) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}W\d{2}$`<br>**Desc:** Production execution week. |
| `planned_run_date` | `str` | Required | Date (YYYY-MM-DD) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}$`<br>**Desc:** Scheduled production run start date. |
| `planned_output_qty` | `float` | Required | Units / Pieces | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 0.0<br>**Desc:** Scheduled production quantity in units. |
| `actual_output_qty` | `float` | Required | Units / Pieces | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 0.0<br>**Desc:** Completed manufacturing output. |
| `status` | `ProductionStatus` | Optional | N/A | Non-Unique | `SCHEDULED, IN_PROGRESS, COMPLETED, DELAYED` | **Rule:** NULLABLE<br>**Desc:** Execution status. |
| `created_at` | `str` | Required | Timestamp ISO-8601 | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$`<br>**Desc:**  |

### Shortage

| Field Name | Type | Status | Units | Uniqueness | Allowed Values | Validation Rules & Description |
|---|---|---|---|---|---|---|
| `shortage_id` | `str` | Required | N/A | Unique | `Any valid type` | **Rule:** PRIMARY KEY; UNIQUE; NOT NULL; regex: `^SHORT-\d{4}-\d{6}$`<br>**Desc:** Primary Key. Identified shortage incident: SHORT-2026-000001. |
| `sku_id` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> SKU.sku_id; NOT NULL; regex: `^SKU-\d{6}$`<br>**Desc:**  |
| `location_id` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> Location.location_id; NOT NULL; regex: `^LOC-\d{4}$`<br>**Desc:**  |
| `shortage_week` | `str` | Required | Week (YYYYWww) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}W\d{2}$`<br>**Desc:** Week where balance is negative or below safety stock. |
| `shortage_date` | `str` | Required | Date (YYYY-MM-DD) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}$`<br>**Desc:** Date of shortage occurrence. |
| `shortage_qty` | `float` | Required | Units / Pieces | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 0.0<br>**Desc:** Net stock deficit in units below zero. |
| `cumulative_shortage_qty` | `float` | Required | Units / Pieces | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 0.0<br>**Desc:** Cumulative unmet demand across horizon. |
| `unmet_demand_qty` | `float` | Required | Units / Pieces | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 0.0<br>**Desc:** Demand unfulfilled in the specific week. |
| `root_cause` | `ShortageRootCause` | Required | N/A | Non-Unique | `DEMAND_SPIKE, LATE_INBOUND, SUPPLIER_CAPACITY_CONSTRAINT, LEAD_TIME_DELAY, QUALITY_HOLD, INITIAL_STOCKOUT` | **Rule:** NOT NULL<br>**Desc:** Explainable primary root cause. |
| `priority_score` | `float` | Required | Ratio / Score (0-1 or 0-100) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 0.0; value <= 100.0<br>**Desc:** Prioritization score based on revenue impact and customer SLA. |
| `priority_rank` | `int` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 1<br>**Desc:** Horizon-wide priority rank (1 = highest severity). |
| `status` | `ShortageStatus` | Optional | N/A | Non-Unique | `OPEN, MITIGATED, UNMITIGATED, IN_REVIEW` | **Rule:** NULLABLE<br>**Desc:** Resolution lifecycle status. |
| `created_at` | `str` | Required | Timestamp ISO-8601 | Non-Unique | `Any valid type` | **Rule:** NOT NULL; regex: `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$`<br>**Desc:**  |

### ShortageEvidence

| Field Name | Type | Status | Units | Uniqueness | Allowed Values | Validation Rules & Description |
|---|---|---|---|---|---|---|
| `evidence_id` | `str` | Required | N/A | Unique | `Any valid type` | **Rule:** PRIMARY KEY; UNIQUE; NOT NULL; regex: `^EVI-\d{4}-\d{6}$`<br>**Desc:** Primary Key. Traceability link: EVI-2026-000001. |
| `shortage_id` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> Shortage.shortage_id; NOT NULL; regex: `^SHORT-\d{4}-\d{6}$`<br>**Desc:**  |
| `source_entity` | `SourceEntityType` | Required | N/A | Non-Unique | `ForecastDemand, PurchaseOrder, Inventory, SupplierCapacity, LeadTime, ProductionPlan` | **Rule:** NOT NULL<br>**Desc:** Source table providing causal evidence. |
| `source_id` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** NOT NULL<br>**Desc:** Primary key of source record. |
| `impact_description` | `str` | Required | Ratio / Score (0-1 or 0-100) | Non-Unique | `Any valid type` | **Rule:** NOT NULL<br>**Desc:** Detailed causal narrative. |
| `metric_value` | `float` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** NOT NULL<br>**Desc:** Numeric evidence metric (e.g. late days, demand spike %) |

### MitigationOption

| Field Name | Type | Status | Units | Uniqueness | Allowed Values | Validation Rules & Description |
|---|---|---|---|---|---|---|
| `mitigation_id` | `str` | Required | N/A | Unique | `Any valid type` | **Rule:** PRIMARY KEY; UNIQUE; NOT NULL; regex: `^MIT-SHORT-\d{4}-\d{6}-\d{2}$`<br>**Desc:** Primary Key. Mitigation option: MIT-SHORT-2026-000001-01. |
| `shortage_id` | `str` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> Shortage.shortage_id; NOT NULL; regex: `^SHORT-\d{4}-\d{6}$`<br>**Desc:**  |
| `action_type` | `MitigationActionType` | Required | N/A | Non-Unique | `EXPEDITE_PO, SUBSTITUTE_SKU, TRANSFER_STOCK, INCREASE_PRODUCTION` | **Rule:** NOT NULL<br>**Desc:** Mitigation resolution mechanism. |
| `substitute_sku_id` | `Optional` | Optional | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> SKU.sku_id; NULLABLE; regex: `^SKU-\d{6}$`<br>**Desc:**  |
| `expedited_po_id` | `Optional` | Optional | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> PurchaseOrder.po_id; NULLABLE; regex: `^PO-\d{4}-\d{6}$`<br>**Desc:**  |
| `alt_location_id` | `Optional` | Optional | N/A | Non-Unique | `Any valid type` | **Rule:** FOREIGN KEY -> Location.location_id; NULLABLE; regex: `^LOC-\d{4}$`<br>**Desc:**  |
| `cost` | `float` | Required | USD | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 0.0<br>**Desc:** Estimated incremental implementation cost in USD. |
| `service_level_impact` | `float` | Required | Ratio / Score (0-1 or 0-100) | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 0.0; value <= 1.0<br>**Desc:** Service level protection ratio (0.0 to 1.0). |
| `lead_time_days` | `int` | Required | Days | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 0<br>**Desc:** Days required to activate this mitigation. |
| `capacity_check_passed` | `bool` | Required | Units / Pieces | Non-Unique | `True, False` | **Rule:** NOT NULL<br>**Desc:** True if supplier/logistics capacity is verified. |
| `policy_check_passed` | `bool` | Required | N/A | Non-Unique | `True, False` | **Rule:** NOT NULL<br>**Desc:** True if business policy rules are satisfied. |
| `score` | `float` | Required | Ratio / Score (0-1 or 0-100) | Non-Unique | `Any valid type` | **Rule:** NOT NULL<br>**Desc:** Multi-criteria weighted optimization score. |
| `rank` | `int` | Required | N/A | Non-Unique | `Any valid type` | **Rule:** NOT NULL; value >= 1<br>**Desc:** Rank among candidate options for this shortage (1 = best). |
| `status` | `MitigationStatus` | Optional | N/A | Non-Unique | `PROPOSED, APPROVED, REJECTED, EXECUTED` | **Rule:** NULLABLE<br>**Desc:** Resolution status. |
