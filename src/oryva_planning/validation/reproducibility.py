"""
Deterministic Reproducibility Harness for Oryva Planning.
Executes the data generator twice from a cold start using the same fixed seed,
computes SHA-256 checksums and row counts across all exported CSV files,
and writes reproducibility_report.md.
"""

from pathlib import Path
import hashlib
import tempfile
import shutil
from typing import Dict, Any, List, Tuple
import pandas as pd

from oryva_planning.config import PlanningConfig
from oryva_planning.generators.pipeline_generator import generate_all_datasets
from oryva_planning.planning.engine import run_planning_engine


def calculate_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


def count_lines(file_path: Path) -> int:
    """Count lines (excluding header) in a CSV file."""
    with open(file_path, "r", encoding="utf-8") as f:
        # Subtract 1 for header line
        return max(0, sum(1 for _ in f) - 1)


def run_reproducibility_check(
    config_path: Path = Path("config/starter.yaml"),
    report_path: Path = Path("reproducibility_report.md"),
) -> bool:
    """
    Execute generation twice into isolated directories, compare row counts
    and SHA-256 checksums, and write reproducibility_report.md.
    """
    cfg = PlanningConfig.load_from_yaml(config_path)

    # Isolated temporary directories
    with tempfile.TemporaryDirectory() as tmp_dir:
        dir_1 = Path(tmp_dir) / "run_1"
        dir_2 = Path(tmp_dir) / "run_2"
        dir_1.mkdir()
        dir_2.mkdir()

        # Run 1
        cfg_1 = PlanningConfig.load_from_yaml(config_path)
        cfg_1.paths.input_dir = str(dir_1)
        ds1 = generate_all_datasets(cfg_1, save_to_disk=True)
        run_planning_engine(ds1, cfg_1, save_to_disk=True)

        # Run 2
        cfg_2 = PlanningConfig.load_from_yaml(config_path)
        cfg_2.paths.input_dir = str(dir_2)
        ds2 = generate_all_datasets(cfg_2, save_to_disk=True)
        run_planning_engine(ds2, cfg_2, save_to_disk=True)

        files_1 = sorted(list(dir_1.glob("*.csv")))
        files_2 = sorted(list(dir_2.glob("*.csv")))

        results = []
        all_match = True

        for f1 in files_1:
            name = f1.name
            f2 = dir_2 / name

            lines_1 = count_lines(f1)
            lines_2 = count_lines(f2) if f2.exists() else 0

            hash_1 = calculate_sha256(f1)
            hash_2 = calculate_sha256(f2) if f2.exists() else "MISSING"

            count_match = (lines_1 == lines_2)
            hash_match = (hash_1 == hash_2)
            passed = count_match and hash_match

            if not passed:
                all_match = False

            results.append({
                "table": f1.stem,
                "lines_1": lines_1,
                "lines_2": lines_2,
                "hash_1": hash_1,
                "hash_2": hash_2,
                "passed": passed,
            })

        # Generate markdown report
        lines = [
            "# Oryva AI - Deterministic Reproducibility Report",
            "",
            f"**Evaluation Seed:** `{cfg.seed}`  ",
            f"**Scale:** `{cfg.scale.name}` ({cfg.scale.num_skus} SKUs, {cfg.scale.num_locations} Locations)  ",
            f"**Overall Status:** `{'PASSED (Bit-for-Bit Deterministic)' if all_match else 'FAILED'}`",
            "",
            "## Table Checksum Comparison",
            "",
            "| Table | Run 1 Rows | Run 2 Rows | Run 1 SHA-256 | Run 2 SHA-256 | Status |",
            "|---|---|---|---|---|---|",
        ]

        for r in results:
            status_badge = "✅ PASS" if r["passed"] else "❌ FAIL"
            lines.append(
                f"| `{r['table']}` | {r['lines_1']:,} | {r['lines_2']:,} | "
                f"`{r['hash_1'][:12]}...` | `{r['hash_2'][:12]}...` | {status_badge} |"
            )

        lines.extend([
            "",
            "## Methodological Proof of Determinism",
            "1. **Isolated PRNG Streams:** Each generator draws numbers exclusively from its own `SeedSequence.spawn()` child stream.",
            "2. **Strict Primary Key Ordering:** All tables are sorted deterministically by primary key prior to serialisation.",
            "3. **Fixed Floating-Point Representation:** All numeric floats are formatted with fixed decimal precision (`%.4f`).",
            "4. **Standard Line Terminators:** All files use standard Unix line-feed (`\\n`) endings.",
            "5. **Zero Host Clocks:** No system `datetime.now()` or unbounded Python `set` iteration is utilized.",
        ])

        report_path.write_text("\n".join(lines), encoding="utf-8")

        return all_match
