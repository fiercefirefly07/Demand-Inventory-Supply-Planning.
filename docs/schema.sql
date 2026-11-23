CREATE TABLE IF NOT EXISTS sku (
sku_id TEXT NOT NULL,
name TEXT NOT NULL,
category TEXT NOT NULL,
unit_of_measure TEXT NOT NULL,
unit_cost REAL NOT NULL,
selling_price REAL NOT NULL,
holding_cost_rate REAL NOT NULL,
lifecycle_status TEXT,
effective_start_date TEXT NOT NULL,
effective_end_date TEXT NOT NULL,
    PRIMARY KEY (sku_id)
);

CREATE TABLE IF NOT EXISTS location (
location_id TEXT NOT NULL,
name TEXT NOT NULL,
type TEXT NOT NULL,
region TEXT NOT NULL,
holding_cost_per_unit_day REAL NOT NULL,
capacity_units INTEGER NOT NULL,
is_active INTEGER,
effective_start_date TEXT NOT NULL,
effective_end_date TEXT NOT NULL,
    PRIMARY KEY (location_id)
);

CREATE TABLE IF NOT EXISTS supplier (
supplier_id TEXT NOT NULL,
name TEXT NOT NULL,
country TEXT NOT NULL,
reliability_score REAL NOT NULL,
tier TEXT NOT NULL,
is_active INTEGER,
effective_start_date TEXT NOT NULL,
effective_end_date TEXT NOT NULL,
    PRIMARY KEY (supplier_id)
);

CREATE TABLE IF NOT EXISTS skusupplier (
sku_supplier_id TEXT NOT NULL,
sku_id TEXT NOT NULL,
supplier_id TEXT NOT NULL,
is_primary INTEGER,
supplier_part_number TEXT NOT NULL,
effective_start_date TEXT NOT NULL,
effective_end_date TEXT NOT NULL,
    PRIMARY KEY (sku_supplier_id)
);

CREATE TABLE IF NOT EXISTS skusubstitute (
substitute_id TEXT NOT NULL,
primary_sku_id TEXT NOT NULL,
substitute_sku_id TEXT NOT NULL,
conversion_rate REAL,
approved INTEGER,
effective_start_date TEXT NOT NULL,
effective_end_date TEXT NOT NULL,
    PRIMARY KEY (substitute_id)
);

CREATE TABLE IF NOT EXISTS forecastdemand (
demand_id TEXT NOT NULL,
sku_id TEXT NOT NULL,
location_id TEXT NOT NULL,
forecast_week TEXT NOT NULL,
forecast_date TEXT NOT NULL,
mean_demand REAL NOT NULL,
forecast_qty REAL NOT NULL,
unit_of_measure TEXT NOT NULL,
    PRIMARY KEY (demand_id)
);

CREATE TABLE IF NOT EXISTS inventory (
inventory_id TEXT NOT NULL,
sku_id TEXT NOT NULL,
location_id TEXT NOT NULL,
on_hand_qty REAL NOT NULL,
safety_stock_qty REAL NOT NULL,
reorder_point REAL NOT NULL,
unit_of_measure TEXT NOT NULL,
effective_date TEXT NOT NULL,
status TEXT,
    PRIMARY KEY (inventory_id)
);

CREATE TABLE IF NOT EXISTS suppliercapacity (
capacity_id TEXT NOT NULL,
supplier_id TEXT NOT NULL,
sku_id TEXT NOT NULL,
period_week TEXT NOT NULL,
max_weekly_capacity REAL NOT NULL,
committed_qty REAL NOT NULL,
available_capacity REAL NOT NULL,
effective_start_date TEXT NOT NULL,
effective_end_date TEXT NOT NULL,
    PRIMARY KEY (capacity_id)
);

CREATE TABLE IF NOT EXISTS leadtime (
lead_time_id TEXT NOT NULL,
supplier_id TEXT NOT NULL,
sku_id TEXT NOT NULL,
destination_location_id TEXT NOT NULL,
planned_lead_time_days INTEGER NOT NULL,
minimum_order_qty REAL NOT NULL,
order_multiple_qty REAL NOT NULL,
expedited_lead_time_days INTEGER NOT NULL,
effective_start_date TEXT NOT NULL,
effective_end_date TEXT NOT NULL,
    PRIMARY KEY (lead_time_id)
);

CREATE TABLE IF NOT EXISTS purchaseorder (
po_id TEXT NOT NULL,
supplier_id TEXT NOT NULL,
sku_id TEXT NOT NULL,
destination_location_id TEXT NOT NULL,
order_qty REAL NOT NULL,
unit_cost REAL NOT NULL,
currency TEXT,
order_date TEXT NOT NULL,
promised_delivery_date TEXT NOT NULL,
revised_delivery_date TEXT NOT NULL,
actual_delivery_date TEXT,
current_status TEXT NOT NULL,
created_at TEXT NOT NULL,
    PRIMARY KEY (po_id)
);

CREATE TABLE IF NOT EXISTS purchaseorderevent (
event_id TEXT NOT NULL,
po_id TEXT NOT NULL,
from_status TEXT,
to_status TEXT NOT NULL,
event_ts TEXT NOT NULL,
event_reason TEXT NOT NULL,
actor TEXT NOT NULL,
    PRIMARY KEY (event_id)
);

CREATE TABLE IF NOT EXISTS productionplan (
plan_id TEXT NOT NULL,
sku_id TEXT NOT NULL,
location_id TEXT NOT NULL,
planned_week TEXT NOT NULL,
planned_run_date TEXT NOT NULL,
planned_output_qty REAL NOT NULL,
actual_output_qty REAL NOT NULL,
status TEXT,
created_at TEXT NOT NULL,
    PRIMARY KEY (plan_id)
);

CREATE TABLE IF NOT EXISTS shortage (
shortage_id TEXT NOT NULL,
sku_id TEXT NOT NULL,
location_id TEXT NOT NULL,
shortage_week TEXT NOT NULL,
shortage_date TEXT NOT NULL,
shortage_qty REAL NOT NULL,
cumulative_shortage_qty REAL NOT NULL,
unmet_demand_qty REAL NOT NULL,
root_cause TEXT NOT NULL,
priority_score REAL NOT NULL,
priority_rank INTEGER NOT NULL,
status TEXT,
created_at TEXT NOT NULL,
    PRIMARY KEY (shortage_id)
);

CREATE TABLE IF NOT EXISTS shortageevidence (
evidence_id TEXT NOT NULL,
shortage_id TEXT NOT NULL,
source_entity TEXT NOT NULL,
source_id TEXT NOT NULL,
impact_description TEXT NOT NULL,
metric_value REAL NOT NULL,
    PRIMARY KEY (evidence_id)
);

CREATE TABLE IF NOT EXISTS mitigationoption (
mitigation_id TEXT NOT NULL,
shortage_id TEXT NOT NULL,
action_type TEXT NOT NULL,
substitute_sku_id TEXT,
expedited_po_id TEXT,
alt_location_id TEXT,
cost REAL NOT NULL,
service_level_impact REAL NOT NULL,
lead_time_days INTEGER NOT NULL,
capacity_check_passed INTEGER NOT NULL,
policy_check_passed INTEGER NOT NULL,
score REAL NOT NULL,
rank INTEGER NOT NULL,
status TEXT,
    PRIMARY KEY (mitigation_id)
);