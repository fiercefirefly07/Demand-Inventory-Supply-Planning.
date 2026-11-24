"""
Unit tests for Phase 4 Planning Engine.
Verifies week-by-week balance reconciliation, shortage detection,
root cause diagnosis, and shortage evidence links.
"""

import pandas as pd
import pytest

from oryva_planning.config import PlanningConfig
from oryva_planning.generators import generate_all_datasets
from oryva_planning.planning import run_planning_engine
from oryva_planning.schema import (
    Shortage,
    ShortageEvidence,
    ShortageRootCause,
    SourceEntityType,
    REGEX_SHORTAGE,
    REGEX_SHORTAGE_EVIDENCE,
)


@pytest.fixture
def starter_config() -> PlanningConfig:
    return PlanningConfig.load_from_yaml("config/starter.yaml")


class TestPlanningEngine:
    """Verify deterministic planning calculations."""

    def test_balance_week_by_week_reconciliation(self, starter_config: PlanningConfig):
        datasets = generate_all_datasets(starter_config, save_to_disk=False)
        results = run_planning_engine(datasets, starter_config, save_to_disk=False)
        df_bal = results["projected_balance"]

        assert len(df_bal) > 0

        # Rule 1: closing balance = opening + inbound - demand
        calculated_closing = (
            df_bal["opening_stock"] + df_bal["total_inbound_qty"] - df_bal["demand_qty"]
        ).round(2)
        diff = (calculated_closing - df_bal["projected_balance"]).abs()
        assert (diff <= 0.01).all(), "Projected balance arithmetic failed reconciliation!"

        # Rule 2: Week-to-week carry forward: opening(w) = max(0, closing(w-1))
        grouped = df_bal.groupby(["sku_id", "location_id"])
        for (sku_id, loc_id), group in list(grouped)[:10]:  # test sample of 10 pairs
            group = group.sort_values(by="week_num").reset_index(drop=True)
            for w in range(1, len(group)):
                prev_closing = group.loc[w - 1, "projected_balance"]
                curr_opening = group.loc[w, "opening_stock"]
                expected_opening = max(0.0, prev_closing)
                assert abs(curr_opening - expected_opening) <= 0.01, (
                    f"Week carry-forward broken for {sku_id}-{loc_id} week {w+1}: "
                    f"prev_closing={prev_closing}, curr_opening={curr_opening}"
                )

    def test_shortages_and_priority_ranking(self, starter_config: PlanningConfig):
        datasets = generate_all_datasets(starter_config, save_to_disk=False)
        results = run_planning_engine(datasets, starter_config, save_to_disk=False)
        df_shortage = results["shortage"]

        if len(df_shortage) > 0:
            assert list(df_shortage.columns) == list(Shortage.model_fields.keys())

            for sid in df_shortage["shortage_id"]:
                assert REGEX_SHORTAGE.match(sid) is not None
            assert df_shortage["shortage_id"].is_monotonic_increasing

            # All shortage quantities must be strictly positive
            assert (df_shortage["shortage_qty"] > 0).all()
            assert (df_shortage["unmet_demand_qty"] > 0).all()
            assert (df_shortage["priority_score"] >= 0.0).all()
            assert (df_shortage["priority_score"] <= 100.0).all()

            # Root cause must be valid enum
            valid_causes = {c.value for c in ShortageRootCause}
            assert set(df_shortage["root_cause"]).issubset(valid_causes)

    def test_shortage_evidence_traceability(self, starter_config: PlanningConfig):
        datasets = generate_all_datasets(starter_config, save_to_disk=False)
        results = run_planning_engine(datasets, starter_config, save_to_disk=False)
        df_shortage = results["shortage"]
        df_evidence = results["shortageevidence"]

        if len(df_shortage) > 0:
            assert len(df_evidence) >= len(df_shortage)
            assert list(df_evidence.columns) == list(ShortageEvidence.model_fields.keys())

            for eid in df_evidence["evidence_id"]:
                assert REGEX_SHORTAGE_EVIDENCE.match(eid) is not None
            assert df_evidence["evidence_id"].is_monotonic_increasing

            # FK check: every evidence record must point to a valid shortage_id
            valid_shortage_ids = set(df_shortage["shortage_id"])
            assert set(df_evidence["shortage_id"]).issubset(valid_shortage_ids)

            # Every shortage must have at least one evidence record!
            evidenced_shortages = set(df_evidence["shortage_id"])
            assert valid_shortage_ids == evidenced_shortages, "Found shortage without causal evidence!"

            # Check valid source entity types
            valid_entities = {e.value for e in SourceEntityType}
            assert set(df_evidence["source_entity"]).issubset(valid_entities)
