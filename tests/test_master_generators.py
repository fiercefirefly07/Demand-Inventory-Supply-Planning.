"""
Comprehensive unit tests for Phase 2 Master Generators.
Verifies determinism, foreign key integrity, business rules,
and Pydantic schema conformance for SKU, Location, Supplier,
and bridge tables.
"""

from pathlib import Path
import pandas as pd
import pytest

from oryva_planning.config import PlanningConfig
from oryva_planning.generators import (
    generate_skus,
    generate_locations,
    generate_suppliers,
    generate_sku_suppliers,
    generate_sku_substitutes,
    generate_master_datasets,
)
from oryva_planning.schema import (
    REGEX_SKU,
    REGEX_LOCATION,
    REGEX_SUPPLIER,
    REGEX_SKU_SUPPLIER,
    REGEX_SKU_SUBSTITUTE,
    SKU,
    Location,
    Supplier,
    SkuSupplier,
    SkuSubstitute,
)


@pytest.fixture
def starter_config() -> PlanningConfig:
    return PlanningConfig.load_from_yaml("config/starter.yaml")


class TestMasterGenerators:
    """Test individual master entity and bridge generation."""

    def test_sku_generator(self, starter_config: PlanningConfig):
        datasets = generate_master_datasets(starter_config, save_to_disk=False)
        df_sku = datasets["sku"]

        assert len(df_sku) == starter_config.scale.num_skus
        assert list(df_sku.columns) == list(SKU.model_fields.keys())

        # Check ID format and sorting
        for sku_id in df_sku["sku_id"]:
            assert REGEX_SKU.match(sku_id) is not None
        assert df_sku["sku_id"].is_monotonic_increasing

        # Check business logic
        assert (df_sku["unit_cost"] > 0).all()
        assert (df_sku["selling_price"] >= df_sku["unit_cost"]).all()
        assert (df_sku["holding_cost_rate"] >= 0.10).all()
        assert (df_sku["holding_cost_rate"] <= 0.30).all()

    def test_location_generator(self, starter_config: PlanningConfig):
        datasets = generate_master_datasets(starter_config, save_to_disk=False)
        df_loc = datasets["location"]

        assert len(df_loc) == starter_config.scale.num_locations
        assert list(df_loc.columns) == list(Location.model_fields.keys())

        for loc_id in df_loc["location_id"]:
            assert REGEX_LOCATION.match(loc_id) is not None
        assert df_loc["location_id"].is_monotonic_increasing

        assert (df_loc["holding_cost_per_unit_day"] > 0).all()
        assert (df_loc["capacity_units"] > 0).all()
        assert df_loc["is_active"].any()

    def test_supplier_generator(self, starter_config: PlanningConfig):
        datasets = generate_master_datasets(starter_config, save_to_disk=False)
        df_sup = datasets["supplier"]

        assert len(df_sup) == starter_config.scale.num_suppliers
        assert list(df_sup.columns) == list(Supplier.model_fields.keys())

        for sup_id in df_sup["supplier_id"]:
            assert REGEX_SUPPLIER.match(sup_id) is not None
        assert df_sup["supplier_id"].is_monotonic_increasing

        assert (df_sup["reliability_score"] >= 0.0).all()
        assert (df_sup["reliability_score"] <= 1.0).all()

    def test_sku_supplier_bridge_rules(self, starter_config: PlanningConfig):
        datasets = generate_master_datasets(starter_config, save_to_disk=False)
        df_sku = datasets["sku"]
        df_sup = datasets["supplier"]
        df_bridge = datasets["sku_supplier"]

        assert list(df_bridge.columns) == list(SkuSupplier.model_fields.keys())

        # FK checks
        valid_skus = set(df_sku["sku_id"])
        valid_sups = set(df_sup["supplier_id"])
        assert set(df_bridge["sku_id"]).issubset(valid_skus)
        assert set(df_bridge["supplier_id"]).issubset(valid_sups)

        # ID pattern
        for bridge_id in df_bridge["sku_supplier_id"]:
            assert REGEX_SKU_SUPPLIER.match(bridge_id) is not None
        assert df_bridge["sku_supplier_id"].is_monotonic_increasing

        # Primary supplier rule: Every SKU must have exactly ONE primary supplier
        primary_counts = df_bridge[df_bridge["is_primary"]].groupby("sku_id")["supplier_id"].count()
        assert len(primary_counts) == len(df_sku)
        assert (primary_counts == 1).all()

    def test_sku_substitute_bridge_rules(self, starter_config: PlanningConfig):
        datasets = generate_master_datasets(starter_config, save_to_disk=False)
        df_sku = datasets["sku"]
        df_sub = datasets["sku_substitute"]

        assert list(df_sub.columns) == list(SkuSubstitute.model_fields.keys())

        if len(df_sub) > 0:
            valid_skus = set(df_sku["sku_id"])
            assert set(df_sub["primary_sku_id"]).issubset(valid_skus)
            assert set(df_sub["substitute_sku_id"]).issubset(valid_skus)

            # No self-substitution
            assert (df_sub["primary_sku_id"] != df_sub["substitute_sku_id"]).all()

            # ID pattern
            for sub_id in df_sub["substitute_id"]:
                assert REGEX_SKU_SUBSTITUTE.match(sub_id) is not None
            assert df_sub["substitute_id"].is_monotonic_increasing

            # In clean baseline, all generated substitutes are approved
            assert df_sub["approved"].all()

            # Same category check
            sku_cat_map = dict(zip(df_sku["sku_id"], df_sku["category"]))
            for _, row in df_sub.iterrows():
                assert sku_cat_map[row["primary_sku_id"]] == sku_cat_map[row["substitute_sku_id"]]


class TestDeterminism:
    """Test seed determinism across runs."""

    def test_reproducibility_across_runs(self, starter_config: PlanningConfig):
        run1 = generate_master_datasets(starter_config, save_to_disk=False)
        run2 = generate_master_datasets(starter_config, save_to_disk=False)

        for key in ["sku", "location", "supplier", "sku_supplier", "sku_substitute"]:
            pd.testing.assert_frame_equal(run1[key], run2[key])


class TestDiskExport:
    """Test saving datasets to disk."""

    def test_csv_export(self, starter_config: PlanningConfig, tmp_path: Path):
        starter_config.paths.input_dir = str(tmp_path)
        datasets = generate_master_datasets(starter_config, save_to_disk=True)

        for name in datasets.keys():
            csv_file = tmp_path / f"{name}.csv"
            assert csv_file.exists()
            assert csv_file.stat().st_size > 0

            # Read back and verify row count
            loaded_df = pd.read_csv(csv_file)
            assert len(loaded_df) == len(datasets[name])
