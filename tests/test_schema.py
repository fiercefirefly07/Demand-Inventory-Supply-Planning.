"""
Comprehensive unit tests for the Oryva Planning schema layer.
Verifies deterministic ID formats, entity models, enums, relationships,
configuration loading, and data dictionary derivation.
"""

import pytest
from pydantic import ValidationError

from oryva_planning.config import PlanningConfig
from oryva_planning.schema import (
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
    AnomalyIssueType,
    SourceEntityType,
    build_sku_id,
    build_location_id,
    build_supplier_id,
    build_demand_id,
    build_inventory_id,
    build_supplier_capacity_id,
    build_lead_time_id,
    build_po_id,
    build_po_event_id,
    build_production_plan_id,
    build_shortage_id,
    build_mitigation_id,
    build_sku_supplier_id,
    build_sku_substitute_id,
    build_shortage_evidence_id,
    parse_week_string,
    REGEX_SKU,
    REGEX_LOCATION,
    REGEX_SUPPLIER,
    REGEX_DEMAND,
    REGEX_INVENTORY,
    REGEX_PO,
    REGEX_SHORTAGE,
    REGEX_MITIGATION,
    SKU,
    Location,
    Supplier,
    SkuSupplier,
    SkuSubstitute,
    ForecastDemand,
    Inventory,
    SupplierCapacity,
    LeadTime,
    PurchaseOrder,
    PurchaseOrderEvent,
    ProductionPlan,
    Shortage,
    ShortageEvidence,
    MitigationOption,
    CORE_ENTITIES,
    ENTITY_RELATIONSHIPS,
    generate_markdown_data_dictionary,
    generate_sql_ddl,
)


class TestIdBuilders:
    """Test deterministic ID generation and regex validation."""

    def test_sku_id_format(self):
        sku_id = build_sku_id(1)
        assert sku_id == "SKU-000001"
        assert REGEX_SKU.match(sku_id) is not None
        assert build_sku_id(3000) == "SKU-003000"

    def test_location_id_format(self):
        loc_id = build_location_id(1)
        assert loc_id == "LOC-0001"
        assert REGEX_LOCATION.match(loc_id) is not None
        assert build_location_id(50) == "LOC-0050"

    def test_supplier_id_format(self):
        sup_id = build_supplier_id(1)
        assert sup_id == "SUP-000001"
        assert REGEX_SUPPLIER.match(sup_id) is not None
        assert build_supplier_id(500) == "SUP-000500"

    def test_demand_id_format(self):
        demand_id = build_demand_id("SKU-000001", "LOC-0001", 2026, 1)
        assert demand_id == "DEM-SKU-000001-LOC-0001-2026W01"
        assert REGEX_DEMAND.match(demand_id) is not None

    def test_inventory_id_format(self):
        inv_id = build_inventory_id("SKU-000001", "LOC-0001")
        assert inv_id == "INV-SKU-000001-LOC-0001"
        assert REGEX_INVENTORY.match(inv_id) is not None

    def test_po_id_format(self):
        po_id = build_po_id(1, 2026)
        assert po_id == "PO-2026-000001"
        assert REGEX_PO.match(po_id) is not None
        assert build_po_id(10000, 2026) == "PO-2026-010000"

    def test_shortage_id_format(self):
        shortage_id = build_shortage_id(1, 2026)
        assert shortage_id == "SHORT-2026-000001"
        assert REGEX_SHORTAGE.match(shortage_id) is not None

    def test_mitigation_id_format(self):
        shortage_id = "SHORT-2026-000001"
        mit_id = build_mitigation_id(shortage_id, 1)
        assert mit_id == "MIT-SHORT-2026-000001-01"
        assert REGEX_MITIGATION.match(mit_id) is not None

    def test_parse_week_string(self):
        year, week = parse_week_string("2026W01")
        assert year == 2026
        assert week == 1
        with pytest.raises(ValueError):
            parse_week_string("invalid-week")


class TestEnums:
    """Test enumeration definitions and contents."""

    def test_anomaly_issue_types(self):
        expected_issues = {
            "double_counted_inbound",
            "unapproved_substitute",
            "supplier_capacity_exceeded",
            "shortage_without_lead_time",
            "uom_mismatch",
        }
        actual_issues = {e.value for e in AnomalyIssueType}
        assert actual_issues == expected_issues

    def test_uom_values(self):
        assert "EA" in [u.value for u in UnitOfMeasure]
        assert "PALLET" in [u.value for u in UnitOfMeasure]

    def test_root_cause_values(self):
        assert ShortageRootCause.DEMAND_SPIKE == "DEMAND_SPIKE"
        assert ShortageRootCause.LATE_INBOUND == "LATE_INBOUND"
        assert ShortageRootCause.SUPPLIER_CAPACITY_CONSTRAINT == "SUPPLIER_CAPACITY_CONSTRAINT"


class TestEntities:
    """Test instantiating valid entities and rejecting invalid records."""

    def test_valid_sku(self):
        sku = SKU(
            sku_id="SKU-000001",
            name="Industrial Valve Assembly",
            category=SkuCategory.FINISHED_GOOD,
            unit_of_measure=UnitOfMeasure.EA,
            unit_cost=45.50,
            selling_price=120.00,
            holding_cost_rate=0.20,
            lifecycle_status=SkuLifecycle.ACTIVE,
            effective_start_date="2026-01-01",
            effective_end_date="2026-12-31",
        )
        assert sku.sku_id == "SKU-000001"
        assert sku.unit_cost == 45.50

    def test_invalid_sku_negative_cost(self):
        with pytest.raises(ValidationError):
            SKU(
                sku_id="SKU-000001",
                name="Bad SKU",
                category=SkuCategory.FINISHED_GOOD,
                unit_of_measure=UnitOfMeasure.EA,
                unit_cost=-10.0,
                selling_price=100.0,
                holding_cost_rate=0.20,
                effective_start_date="2026-01-01",
                effective_end_date="2026-12-31",
            )

    def test_invalid_sku_id_pattern(self):
        with pytest.raises(ValidationError):
            SKU(
                sku_id="INVALID-SKU-1",
                name="Bad ID SKU",
                category=SkuCategory.FINISHED_GOOD,
                unit_of_measure=UnitOfMeasure.EA,
                unit_cost=10.0,
                selling_price=100.0,
                holding_cost_rate=0.20,
                effective_start_date="2026-01-01",
                effective_end_date="2026-12-31",
            )

    def test_valid_location(self):
        loc = Location(
            location_id="LOC-0001",
            name="Chicago Central Distribution Center",
            type=LocationType.CENTRAL_HUB,
            region="Midwest",
            holding_cost_per_unit_day=0.05,
            capacity_units=500000,
            is_active=True,
            effective_start_date="2026-01-01",
            effective_end_date="2026-12-31",
        )
        assert loc.location_id == "LOC-0001"

    def test_valid_supplier(self):
        sup = Supplier(
            supplier_id="SUP-000001",
            name="Apex Precision Components",
            country="USA",
            reliability_score=0.96,
            tier=SupplierTier.STRATEGIC,
            is_active=True,
            effective_start_date="2026-01-01",
            effective_end_date="2026-12-31",
        )
        assert sup.supplier_id == "SUP-000001"

    def test_valid_purchase_order_and_event(self):
        po = PurchaseOrder(
            po_id="PO-2026-000001",
            supplier_id="SUP-000001",
            sku_id="SKU-000001",
            destination_location_id="LOC-0001",
            order_qty=500.0,
            unit_cost=42.00,
            currency="USD",
            order_date="2026-01-05",
            promised_delivery_date="2026-01-19",
            revised_delivery_date="2026-01-19",
            actual_delivery_date=None,
            current_status=POStatus.CONFIRMED,
            created_at="2026-01-05T08:00:00Z",
        )
        assert po.po_id == "PO-2026-000001"

        poe = PurchaseOrderEvent(
            event_id="POE-2026-000001",
            po_id=po.po_id,
            from_status=POStatus.DRAFT,
            to_status=POStatus.CONFIRMED,
            event_ts="2026-01-05T08:30:00Z",
            event_reason="Supplier confirmed order receipt and schedule",
            actor="SupplierPortal",
        )
        assert poe.event_id == "POE-2026-000001"
        assert poe.po_id == po.po_id

    def test_valid_shortage_and_mitigation(self):
        shortage = Shortage(
            shortage_id="SHORT-2026-000001",
            sku_id="SKU-000001",
            location_id="LOC-0001",
            shortage_week="2026W04",
            shortage_date="2026-01-26",
            shortage_qty=120.0,
            cumulative_shortage_qty=120.0,
            unmet_demand_qty=120.0,
            root_cause=ShortageRootCause.LATE_INBOUND,
            priority_score=88.5,
            priority_rank=1,
            status=ShortageStatus.OPEN,
            created_at="2026-01-26T00:00:00Z",
        )
        assert shortage.shortage_id == "SHORT-2026-000001"

        mit = MitigationOption(
            mitigation_id="MIT-SHORT-2026-000001-01",
            shortage_id=shortage.shortage_id,
            action_type=MitigationActionType.EXPEDITE_PO,
            substitute_sku_id=None,
            expedited_po_id="PO-2026-000001",
            alt_location_id=None,
            cost=250.0,
            service_level_impact=0.95,
            lead_time_days=3,
            capacity_check_passed=True,
            policy_check_passed=True,
            score=0.87,
            rank=1,
            status=MitigationStatus.PROPOSED,
        )
        assert mit.mitigation_id == "MIT-SHORT-2026-000001-01"

        evidence = ShortageEvidence(
            evidence_id="EVI-2026-000001",
            shortage_id=shortage.shortage_id,
            source_entity=SourceEntityType.PURCHASE_ORDER,
            source_id="PO-2026-000001",
            impact_description="Inbound PO revised delivery date delayed past requirement week",
            metric_value=7.0,
        )
        assert evidence.evidence_id == "EVI-2026-000001"


class TestConfigAndDataDictionary:
    """Test YAML configuration loader and automatic data dictionary generator."""

    def test_load_starter_config(self):
        cfg = PlanningConfig.load_from_yaml("config/starter.yaml")
        assert cfg.seed == 20261022
        assert cfg.scale.name == "starter"
        assert cfg.scale.num_skus == 50
        assert cfg.scale.num_locations == 5
        assert cfg.scale.num_suppliers == 10
        assert cfg.scale.num_inbound_pos == 100
        assert cfg.anomaly_injection.enabled is True

    def test_load_full_config(self):
        cfg = PlanningConfig.load_from_yaml("config/full.yaml")
        assert cfg.seed == 20261022
        assert cfg.scale.name == "full"
        assert cfg.scale.num_skus == 3000
        assert cfg.scale.num_locations == 50
        assert cfg.scale.num_suppliers == 500
        assert cfg.scale.num_inbound_pos == 10000

    def test_entity_registry_completeness(self):
        assert len(CORE_ENTITIES) == 15
        expected_keys = {
            "SKU", "Location", "Supplier", "SkuSupplier", "SkuSubstitute",
            "ForecastDemand", "Inventory", "SupplierCapacity", "LeadTime",
            "PurchaseOrder", "PurchaseOrderEvent", "ProductionPlan",
            "Shortage", "ShortageEvidence", "MitigationOption"
        }
        assert set(CORE_ENTITIES.keys()) == expected_keys

    def test_relationships_reference_valid_entities(self):
        for rel in ENTITY_RELATIONSHIPS:
            assert rel["parent"] in CORE_ENTITIES, f"Invalid parent: {rel['parent']}"
            assert rel["child"] in CORE_ENTITIES, f"Invalid child: {rel['child']}"

    def test_generate_markdown_data_dictionary(self):
        md = generate_markdown_data_dictionary()
        assert "# Oryva AI - Comprehensive Data Dictionary" in md
        for entity in CORE_ENTITIES.keys():
            assert f"### {entity}" in md

    def test_generate_sql_ddl(self):
        ddl = generate_sql_ddl()
        assert "CREATE TABLE IF NOT EXISTS sku" in ddl
        assert "CREATE TABLE IF NOT EXISTS purchaseorder" in ddl
        assert "PRIMARY KEY" in ddl
