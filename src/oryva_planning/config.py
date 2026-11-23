"""
Configuration models and loader for Oryva Planning.
Loads YAML configuration with strict validation and sane defaults.
"""

from pathlib import Path
from typing import Optional
import yaml
from pydantic import BaseModel, Field


class ScaleConfig(BaseModel):
    name: str = Field(default="starter", description="Scale profile name (starter or full)")
    num_skus: int = Field(default=50, ge=1, description="Total number of unique SKUs")
    num_locations: int = Field(default=5, ge=1, description="Total number of facilities/locations")
    num_suppliers: int = Field(default=10, ge=1, description="Total number of suppliers")
    num_inbound_pos: int = Field(default=100, ge=1, description="Number of baseline inbound POs")
    avg_substitutes_per_sku: int = Field(default=1, ge=0, description="Average substitute options per SKU")
    avg_suppliers_per_sku: int = Field(default=2, ge=1, description="Average qualified suppliers per SKU")


class AnomalyInjectionConfig(BaseModel):
    enabled: bool = Field(default=True, description="Whether to inject synthetic anomalies")
    inbound_double_count_n: int = Field(default=2, ge=0, description="Count of double-counted POs")
    unapproved_substitute_n: int = Field(default=2, ge=0, description="Count of unapproved substitute records")
    supplier_capacity_exceeded_n: int = Field(default=2, ge=0, description="Count of POs exceeding supplier capacity")
    shortage_without_lead_time_n: int = Field(default=2, ge=0, description="Count of shortages evaluated without LT")
    uom_mismatch_n: int = Field(default=2, ge=0, description="Count of unit of measure discrepancies")


class MitigationWeights(BaseModel):
    service_level: float = Field(default=0.50, ge=0.0, le=1.0)
    cost: float = Field(default=0.30, ge=0.0, le=1.0)
    lead_time: float = Field(default=0.20, ge=0.0, le=1.0)


class MitigationConfig(BaseModel):
    weights: MitigationWeights = Field(default_factory=MitigationWeights)


class PathsConfig(BaseModel):
    input_dir: str = Field(default="data/inputs")
    ground_truth_dir: str = Field(default="data/ground_truth")
    export_dir: str = Field(default="data/exports")


class PlanningConfig(BaseModel):
    seed: int = Field(default=20261022, description="Master random seed for SeedSequence")
    year: int = Field(default=2026, description="Planning year")
    planning_horizon_weeks: int = Field(default=52, ge=1, le=53, description="Weeks in planning horizon")
    description: Optional[str] = None
    scale: ScaleConfig = Field(default_factory=ScaleConfig)
    anomaly_injection: AnomalyInjectionConfig = Field(default_factory=AnomalyInjectionConfig)
    mitigation: MitigationConfig = Field(default_factory=MitigationConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)

    @classmethod
    def load_from_yaml(cls, path: str | Path) -> "PlanningConfig":
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f) or {}
        return cls(**raw_data)
