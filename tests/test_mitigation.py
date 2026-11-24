"""
Unit tests for Phase 5 Mitigation Options Engine.
Verifies candidate generation, multi-criteria trade-off scoring,
ranking, and policy/capacity checks.
"""

import pandas as pd
import pytest

from oryva_planning.config import PlanningConfig
from oryva_planning.generators import generate_all_datasets
from oryva_planning.planning import run_planning_engine
from oryva_planning.schema import (
    MitigationOption,
    MitigationActionType,
    REGEX_MITIGATION,
)


@pytest.fixture
def starter_config() -> PlanningConfig:
    return PlanningConfig.load_from_yaml("config/starter.yaml")


class TestMitigationEngine:
    """Verify mitigation candidate generation and ranking."""

    def test_mitigation_options_generated_and_ranked(self, starter_config: PlanningConfig):
        datasets = generate_all_datasets(starter_config, save_to_disk=False)
        results = run_planning_engine(datasets, starter_config, save_to_disk=False)
        df_shortage = results["shortage"]
        df_mit = results["mitigationoption"]

        if len(df_shortage) > 0:
            assert len(df_mit) >= len(df_shortage)
            assert list(df_mit.columns) == list(MitigationOption.model_fields.keys())

            for mid in df_mit["mitigation_id"]:
                assert REGEX_MITIGATION.match(mid) is not None
            assert df_mit["mitigation_id"].is_monotonic_increasing

            # Verify every shortage has candidate options
            shortages_with_mit = set(df_mit["shortage_id"])
            all_shortages = set(df_shortage["shortage_id"])
            assert all_shortages == shortages_with_mit

            # Verify ranking per shortage
            grouped = df_mit.groupby("shortage_id")
            for sid, group in grouped:
                ranks = group["rank"].tolist()
                assert ranks == list(range(1, len(ranks) + 1)), f"Ranks for {sid} not sequential starting at 1: {ranks}"
                # Rank 1 must have highest score in group
                scores = group["score"].tolist()
                assert scores == sorted(scores, reverse=True), f"Scores for {sid} not descending with rank: {scores}"

            # Policy and capacity check rules
            assert df_mit["capacity_check_passed"].all()
            assert df_mit["policy_check_passed"].all()

            # Cost and lead time positive
            assert (df_mit["cost"] > 0.0).all()
            assert (df_mit["lead_time_days"] >= 0).all()
            assert (df_mit["service_level_impact"] >= 0.0).all()
            assert (df_mit["service_level_impact"] <= 1.0).all()
