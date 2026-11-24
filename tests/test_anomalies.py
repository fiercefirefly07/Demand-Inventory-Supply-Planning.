"""
Unit tests for Phase 6 Anomaly Injectors, Detectors, and Ground Truth Wall.
Verifies:
1. Strict Ground Truth Wall: NO ground truth column in clean input tables.
2. Labelled injection of all 5 required edge cases.
3. Precision, Recall, and F1 evaluation of SQL/DataFrame detectors.
"""

from pathlib import Path
import pandas as pd
import pytest

from oryva_planning.config import PlanningConfig
from oryva_planning.generators import generate_all_datasets
from oryva_planning.anomalies import inject_anomalies, evaluate_anomaly_detection
from oryva_planning.schema.enums import AnomalyIssueType


@pytest.fixture
def starter_config() -> PlanningConfig:
    return PlanningConfig.load_from_yaml("config/starter.yaml")


class TestGroundTruthWall:
    """Verify strict isolation between clean inputs and ground truth."""

    def test_clean_inputs_never_leak_ground_truth_columns(self, starter_config: PlanningConfig):
        """Rule: A test that fails if any issue_type or ground-truth column appears in an input table."""
        clean_datasets = generate_all_datasets(starter_config, save_to_disk=False)
        prohibited_columns = {"issue_type", "anomaly_id", "expected_detection_rule", "ground_truth"}

        for table_name, df in clean_datasets.items():
            cols = set(df.columns)
            overlap = cols & prohibited_columns
            assert not overlap, f"Ground truth wall violation in {table_name}: contained {overlap}"


class TestAnomalyInjectionAndDetection:
    """Verify injection mechanics and detector precision/recall metrics."""

    def test_all_five_anomalies_injected_and_recorded(self, starter_config: PlanningConfig, tmp_path: Path):
        starter_config.paths.ground_truth_dir = str(tmp_path)
        clean_datasets = generate_all_datasets(starter_config, save_to_disk=False)

        injected_datasets, gt_df = inject_anomalies(clean_datasets, starter_config, save_ground_truth=True)

        # Verify ground truth file created
        gt_file = tmp_path / "ground_truth.csv"
        assert gt_file.exists()
        assert len(gt_df) > 0

        # Verify all 5 issue types are represented
        expected_types = {e.value for e in AnomalyIssueType}
        actual_types = set(gt_df["issue_type"])
        assert actual_types == expected_types

        # Verify ground truth schema
        expected_cols = {"anomaly_id", "issue_type", "table_name", "affected_id", "expected_detection_rule", "details"}
        assert set(gt_df.columns) == expected_cols

    def test_detector_precision_and_recall(self, starter_config: PlanningConfig):
        clean_datasets = generate_all_datasets(starter_config, save_to_disk=False)
        injected_datasets, gt_df = inject_anomalies(clean_datasets, starter_config, save_ground_truth=False)

        eval_results = evaluate_anomaly_detection(injected_datasets, gt_df)
        overall = eval_results["overall"]

        # Precision and recall must be high (1.0 for these deterministic rule detectors)
        assert overall["precision"] >= 0.95, f"Detector precision too low: {overall['precision']}"
        assert overall["recall"] >= 0.95, f"Detector recall too low: {overall['recall']}"
        assert overall["f1"] >= 0.95, f"Detector F1 too low: {overall['f1']}"

        # Check each specific issue type achieves 100% precision & recall
        for issue_type, metrics in eval_results["by_issue"].items():
            assert metrics["precision"] == 1.0, f"Precision failed for {issue_type}: {metrics}"
            assert metrics["recall"] == 1.0, f"Recall failed for {issue_type}: {metrics}"
