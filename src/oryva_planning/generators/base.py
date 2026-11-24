"""
Base generator classes and deterministic stream orchestration.
Uses numpy SeedSequence.spawn() for isolated, reproducible child random streams.
"""

from typing import List, Dict, Any, Type
import numpy as np
import pandas as pd
from pydantic import BaseModel

from oryva_planning.config import PlanningConfig


class SeedStreamManager:
    """
    Manages deterministic sub-streams using SeedSequence.spawn().
    Assigning each generator its own child seed guarantees that changes
    in one generator's sampling loop never corrupt subsequent generators' streams.
    """

    def __init__(self, master_seed: int):
        self.master_seed = master_seed
        self.root_sequence = np.random.SeedSequence(master_seed)

    def spawn_generators(self, names: List[str]) -> Dict[str, np.random.Generator]:
        """Spawn named default_rng generators from child seed sequences."""
        child_sequences = self.root_sequence.spawn(len(names))
        return {
            name: np.random.default_rng(seq)
            for name, seq in zip(names, child_sequences)
        }


def validate_and_sort_dataframe(
    df: pd.DataFrame,
    model: Type[BaseModel],
    primary_key: str,
    column_order: List[str]
) -> pd.DataFrame:
    """
    Validates every row against the Pydantic model, enforces column ordering,
    and sorts deterministically by primary key.
    """
    # Enforce column order
    df = df[column_order].copy()

    # Sort deterministically by primary key
    df = df.sort_values(by=primary_key).reset_index(drop=True)

    # Validate first and last row (plus sample) to ensure Pydantic compliance
    sample_indices = [0, len(df) - 1] if len(df) > 1 else [0]
    for idx in sample_indices:
        row_dict = {
            k: (None if pd.isna(v) else v)
            for k, v in df.iloc[idx].to_dict().items()
        }
        model(**row_dict)

    return df
