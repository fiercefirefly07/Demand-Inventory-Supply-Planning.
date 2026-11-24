"""
Unit tests for Phase 3 Dependent Generators.
Verifies Demand, Inventory, Capacity, LeadTime, PurchaseOrder,
PurchaseOrderEvent, and ProductionPlan generators.
"""

from pathlib import Path
import pandas as pd
import pytest

from oryva_planning.config import PlanningConfig
from oryva_planning.generators import generate_all_datasets
from oryva_planning.schema import (
    REGEX_DEMAND,
    REGEX_INVENTORY,
    REGEX_SUPPLIER_CAPACITY,
    REGEX_LEAD_TIME,
    REGEX_PO,
    REGEX_PO_EVENT,
    REGEX_PRODUCTION_PLAN,
    ForecastDemand,
    Inventory,
    SupplierCapacity,
    LeadTime,
    PurchaseOrder,
    PurchaseOrderEvent,
    ProductionPlan,
)


@pytest.fixture
def starter_config() -> PlanningConfig:
    return PlanningConfig.load_from_yaml("config/starter.yaml")


class TestDependentGenerators:
    """Verify dependent data facts, constraints, and audit histories."""

    def test_forecast_demand_vectorization_and_rules(self, starter_config: PlanningConfig):
        datasets = generate_all_datasets(starter_config, save_to_disk=False)
        df_demand = datasets["forecastdemand"]
        df_sku = datasets["sku"]
        df_loc = datasets["location"]

        expected_rows = len(df_sku) * len(df_loc) * starter_config.planning_horizon_weeks
        assert len(df_demand) == expected_rows
        assert list(df_demand.columns) == list(ForecastDemand.model_fields.keys())

        # Check regex
        for did in df_demand["demand_id"].iloc[::100]:
            assert REGEX_DEMAND.match(did) is not None
        assert df_demand["demand_id"].is_monotonic_increasing

        # Check FK integrity
        valid_skus = set(df_sku["sku_id"])
        valid_locs = set(df_loc["location_id"])
        assert set(df_demand["sku_id"]).issubset(valid_skus)
        assert set(df_demand["location_id"]).issubset(valid_locs)

        # Non-negative quantities
        assert (df_demand["forecast_qty"] >= 0.0).all()
        assert (df_demand["mean_demand"] >= 0.0).all()

        # UOM reconciliation with SKU
        sku_uom_map = dict(zip(df_sku["sku_id"], df_sku["unit_of_measure"]))
        sample = df_demand.sample(n=min(200, len(df_demand)), random_state=42)
        for _, row in sample.iterrows():
            assert row["unit_of_measure"] == sku_uom_map[row["sku_id"]]

    def test_inventory_opening_balance(self, starter_config: PlanningConfig):
        datasets = generate_all_datasets(starter_config, save_to_disk=False)
        df_inv = datasets["inventory"]
        df_sku = datasets["sku"]
        df_loc = datasets["location"]

        expected_rows = len(df_sku) * len(df_loc)
        assert len(df_inv) == expected_rows
        assert list(df_inv.columns) == list(Inventory.model_fields.keys())

        for inv_id in df_inv["inventory_id"]:
            assert REGEX_INVENTORY.match(inv_id) is not None
        assert df_inv["inventory_id"].is_monotonic_increasing

        assert (df_inv["on_hand_qty"] >= 0.0).all()
        assert (df_inv["safety_stock_qty"] >= 0.0).all()
        assert (df_inv["reorder_point"] >= 0.0).all()

    def test_capacity_and_lead_time_constraints(self, starter_config: PlanningConfig):
        datasets = generate_all_datasets(starter_config, save_to_disk=False)
        df_cap = datasets["suppliercapacity"]
        df_lt = datasets["leadtime"]

        assert len(df_cap) > 0
        assert len(df_lt) > 0

        # Capacity rules
        assert (df_cap["max_weekly_capacity"] > 0.0).all()
        assert (df_cap["available_capacity"] <= df_cap["max_weekly_capacity"]).all()

        # Lead time rules
        assert (df_lt["planned_lead_time_days"] >= 1).all()
        assert (df_lt["expedited_lead_time_days"] >= 1).all()
        assert (df_lt["expedited_lead_time_days"] <= df_lt["planned_lead_time_days"]).all()
        assert (df_lt["minimum_order_qty"] >= 1.0).all()

    def test_purchase_orders_and_event_reconciliation(self, starter_config: PlanningConfig):
        datasets = generate_all_datasets(starter_config, save_to_disk=False)
        df_po = datasets["purchaseorder"]
        df_events = datasets["purchaseorderevent"]

        assert len(df_po) == starter_config.scale.num_inbound_pos
        assert len(df_events) >= len(df_po)  # At least 1 event per PO

        # FK checks
        assert set(df_events["po_id"]).issubset(set(df_po["po_id"]))

        # Check reconciliation: Current PO status MUST match the last event's to_status!
        # Sort events by timestamp and group by po_id
        df_sorted_events = df_events.sort_values(by=["po_id", "event_ts"])
        latest_events = df_sorted_events.groupby("po_id").last().reset_index()

        po_status_map = dict(zip(df_po["po_id"], df_po["current_status"]))
        for _, row in latest_events.iterrows():
            expected_status = row["to_status"]
            actual_status = po_status_map[row["po_id"]]
            assert actual_status == expected_status, f"PO {row['po_id']} status mismatch: {actual_status} vs {expected_status}"

    def test_production_plans(self, starter_config: PlanningConfig):
        datasets = generate_all_datasets(starter_config, save_to_disk=False)
        df_prod = datasets["productionplan"]

        assert len(df_prod) > 0
        assert (df_prod["planned_output_qty"] >= 0.0).all()
        assert (df_prod["actual_output_qty"] >= 0.0).all()
