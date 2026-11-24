"""
Synthetic Supplier Master Data Generator.
Generates supplier base with realistic reliability distributions,
strategic tiers, and country allocations.
"""

from typing import List
import numpy as np
import pandas as pd

from oryva_planning.schema.enums import SupplierTier
from oryva_planning.schema.id_builders import build_supplier_id
from oryva_planning.schema.entities import Supplier
from oryva_planning.generators.base import validate_and_sort_dataframe

SUPPLIER_NAMES_PREFIX = [
    "Apex", "Vanguard", "Titan", "Pinnacle", "OmniTech", "Precision",
    "Alliance", "Nexus", "Summit", "Sterling", "Quantum", "Horizon",
    "Frontier", "Vertex", "Prime", "Atlas", "Cascade", "Zenith"
]

SUPPLIER_NAMES_SUFFIX = [
    "Components", "Precision Works", "Materials", "Industrial Solutions",
    "Manufacturing", "Technologies", "Global Supplies", "Holdings",
    "Fabrication", "Logistics & Supply", "Foundry", "Dynamics"
]

COUNTRIES = [
    ("USA", 0.35),
    ("Germany", 0.15),
    ("Japan", 0.12),
    ("Taiwan", 0.10),
    ("South Korea", 0.08),
    ("Mexico", 0.08),
    ("Canada", 0.05),
    ("China", 0.05),
    ("Netherlands", 0.02),
]


def generate_suppliers(num_suppliers: int, rng: np.random.Generator, year: int = 2026) -> pd.DataFrame:
    """
    Generate deterministic master Supplier records.
    - Reliability scores: bimodal distribution:
      * 85% reliable suppliers: Beta(18, 2) shifted/scaled -> ~0.90 - 0.99
      * 15% unreliable suppliers: Beta(6, 3) shifted/scaled -> ~0.60 - 0.82
    - Tiers: 15% STRATEGIC, 35% TIER_1, 35% TIER_2, 15% COMMODITY
    """
    supplier_ids = [build_supplier_id(i + 1) for i in range(num_suppliers)]

    # Countries based on defined probability distribution
    country_list = [c[0] for c in COUNTRIES]
    country_probs = [c[1] for c in COUNTRIES]
    countries = rng.choice(country_list, size=num_suppliers, p=country_probs)

    # Tiers
    tiers = [
        SupplierTier.STRATEGIC.value,
        SupplierTier.TIER_1.value,
        SupplierTier.TIER_2.value,
        SupplierTier.COMMODITY.value,
    ]
    tier_probs = [0.15, 0.35, 0.35, 0.15]
    selected_tiers = [str(t) for t in rng.choice(tiers, size=num_suppliers, p=tier_probs)]

    # Reliability scores: Mixture model to satisfy "share of unreliable suppliers" requirement
    is_unreliable = rng.random(size=num_suppliers) < 0.15
    reliability_scores = np.zeros(num_suppliers, dtype=float)

    # Reliable group (85%)
    reliable_count = int(np.sum(~is_unreliable))
    if reliable_count > 0:
        # Uniform/Beta clustered between 0.88 and 0.99
        rel_vals = rng.beta(a=16, b=2, size=reliable_count)
        # Scaled to [0.85, 0.99]
        reliability_scores[~is_unreliable] = np.round(0.85 + rel_vals * 0.14, 4)

    # Unreliable group (15%)
    unreliable_count = int(np.sum(is_unreliable))
    if unreliable_count > 0:
        # Beta clustered between 0.60 and 0.82
        unrel_vals = rng.beta(a=6, b=3, size=unreliable_count)
        # Scaled to [0.60, 0.82]
        reliability_scores[is_unreliable] = np.round(0.60 + unrel_vals * 0.22, 4)

    # Strategic suppliers should have high reliability
    for i in range(num_suppliers):
        if selected_tiers[i] == SupplierTier.STRATEGIC.value and reliability_scores[i] < 0.85:
            reliability_scores[i] = round(float(rng.uniform(0.92, 0.98)), 4)

    # Deterministic supplier names
    names = []
    for i in range(num_suppliers):
        prefix = rng.choice(SUPPLIER_NAMES_PREFIX)
        suffix = rng.choice(SUPPLIER_NAMES_SUFFIX)
        supplier_num = (i // (len(SUPPLIER_NAMES_PREFIX) * len(SUPPLIER_NAMES_SUFFIX))) + 1
        num_tag = f" {supplier_num}" if supplier_num > 1 else ""
        country_code = countries[i][:3].upper()
        names.append(f"{prefix} {suffix}{num_tag} ({country_code})")

    # Mostly active
    is_active = [bool(a) for a in rng.choice([True, False], size=num_suppliers, p=[0.97, 0.03])]
    for k in range(min(5, num_suppliers)):
        is_active[k] = True

    df = pd.DataFrame({
        "supplier_id": supplier_ids,
        "name": names,
        "country": countries,
        "reliability_score": reliability_scores,
        "tier": selected_tiers,
        "is_active": is_active,
        "effective_start_date": f"{year}-01-01",
        "effective_end_date": f"{year}-12-31",
    })

    column_order = list(Supplier.model_fields.keys())
    return validate_and_sort_dataframe(df, Supplier, "supplier_id", column_order)
