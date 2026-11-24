"""
Planning Engine Master Coordinator for Oryva Planning.
Executes end-to-end planning run:
1. Calculates week-by-week projected available balance.
2. Identifies inventory shortages and computes priority scores and ranks.
3. Diagnoses explainable root causes and populates ShortageEvidence table.
"""

from pathlib import Path
from typing import Dict, Tuple
import pandas as pd

from oryva_planning.config import PlanningConfig
from oryva_planning.planning.balance import compute_projected_available_balance
from oryva_planning.planning.shortage import identify_and_prioritize_shortages
from oryva_planning.planning.root_cause import diagnose_root_causes_and_evidence
from oryva_planning.planning.mitigation import generate_mitigation_options


def run_planning_engine(
    datasets: Dict[str, pd.DataFrame],
    config: PlanningConfig,
    save_to_disk: bool = True,
) -> Dict[str, pd.DataFrame]:
    """
    Execute planning engine over input datasets.
    Derives balance, shortages, root causes, evidence, and ranked mitigations.
    """
    sku_df = datasets["sku"]
    location_df = datasets["location"]
    inventory_df = datasets["inventory"]
    demand_df = datasets["forecastdemand"]
    po_df = datasets["purchaseorder"]
    production_df = datasets["productionplan"]
    capacity_df = datasets["suppliercapacity"]
    lead_time_df = datasets["leadtime"]
    substitute_df = datasets["sku_substitute"]

    # 1. Compute Projected Available Balance
    balance_df = compute_projected_available_balance(
        sku_df,
        location_df,
        inventory_df,
        demand_df,
        po_df,
        production_df,
        config.planning_horizon_weeks,
        config.year,
    )

    # 2. Identify & Prioritize Shortages
    shortage_raw_df = identify_and_prioritize_shortages(
        balance_df,
        sku_df,
        location_df,
        config.year,
    )

    # 3. Diagnose Root Causes and Traceability Evidence
    shortage_df, evidence_df = diagnose_root_causes_and_evidence(
        shortage_raw_df,
        demand_df,
        inventory_df,
        po_df,
        capacity_df,
        lead_time_df,
        config.year,
    )

    # 4. Generate Candidate Mitigation Options with Trade-off Ranks
    mitigation_df = generate_mitigation_options(
        shortage_df,
        sku_df,
        location_df,
        inventory_df,
        po_df,
        substitute_df,
        lead_time_df,
        config,
    )

    planning_results = {
        "projected_balance": balance_df,
        "shortage": shortage_df,
        "shortageevidence": evidence_df,
        "mitigationoption": mitigation_df,
    }

    if save_to_disk:
        out_dir = Path(config.paths.input_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        for name, df in planning_results.items():
            csv_path = out_dir / f"{name}.csv"
            df.to_csv(csv_path, index=False, lineterminator="\n", float_format="%.4f")

    return planning_results
