"""
Unit tests for Phase 7 DuckDB SQL Validators and Reproducibility Harness.
Verifies all declarative SQL assertions pass and generator reproduces bit-for-bit.
"""

from pathlib import Path
import pytest

from oryva_planning.config import PlanningConfig
from oryva_planning.generators import generate_all_datasets
from oryva_planning.planning import run_planning_engine
from oryva_planning.validation import DuckDBValidationSuite, run_reproducibility_check


@pytest.fixture
def starter_config() -> PlanningConfig:
    return PlanningConfig.load_from_yaml("config/starter.yaml")


class TestDuckDBSQLValidation:
    """Verify DuckDB SQL integrity checks across all generated planning tables."""

    def test_sql_assertions_all_pass(self, starter_config: PlanningConfig):
        datasets = generate_all_datasets(starter_config, save_to_disk=False)
        planning_results = run_planning_engine(datasets, starter_config, save_to_disk=False)

        # Merge datasets for end-to-end SQL verification
        all_tables = {**datasets, **planning_results}

        suite = DuckDBValidationSuite(all_tables)
        eval_summary = suite.run_all_checks()
        suite.close()

        assert eval_summary["all_passed"] is True, f"SQL validation checks failed: {eval_summary['results']}"
        assert eval_summary["failed_checks"] == 0
        assert eval_summary["passed_checks"] == eval_summary["total_checks"]


class TestReproducibilityHarness:
    """Verify bit-for-bit determinism across cold generation runs."""

    def test_reproducibility_check(self, starter_config: PlanningConfig, tmp_path: Path):
        report_file = tmp_path / "reproducibility_report.md"
        is_reproducible = run_reproducibility_check(
            config_path=Path("config/starter.yaml"),
            report_path=report_file,
        )

        assert is_reproducible is True, "Generator output was not deterministic across identical seed runs!"
        assert report_file.exists()
        content = report_file.read_text(encoding="utf-8")
        assert "PASSED (Bit-for-Bit Deterministic)" in content
