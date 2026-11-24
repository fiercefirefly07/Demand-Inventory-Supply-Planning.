"""
Synthetic SKU Master Data Generator.
Generates realistic SKU catalog with lognormal costs, Pareto popularity distributions,
and category-specific units of measure.
"""

from typing import List, Tuple
import numpy as np
import pandas as pd

from oryva_planning.schema.enums import SkuCategory, UnitOfMeasure, SkuLifecycle
from oryva_planning.schema.id_builders import build_sku_id
from oryva_planning.schema.entities import SKU
from oryva_planning.generators.base import validate_and_sort_dataframe

NAME_PREFIXES = [
    "Precision", "Ultra", "Heavy-Duty", "Modular", "Compact", "High-Flow",
    "Standard", "Industrial", "Reinforced", "Eco-Grade", "Micro", "Advanced",
    "Aero-Spec", "Pro-Series", "Custom", "Dynamic", "Thermal", "Optima"
]

NOUNS_BY_CATEGORY = {
    SkuCategory.RAW_MATERIAL.value: [
        "Steel Sheet", "Copper Ingot", "Polymer Resin", "Aluminum Alloy",
        "Silicone Compound", "Titanium Rod", "Ceramic Powder", "Carbon Fiber"
    ],
    SkuCategory.PACKAGING.value: [
        "Corrugated Box", "Thermal Foam Liner", "Bubble Wrap Roll", "Stretch Film",
        "Pallet Crate", "Security Seal Label", "Desiccant Pouch", "Barrier Bag"
    ],
    SkuCategory.SUBASSEMBLY.value: [
        "Servo Actuator", "Hydraulic Manifold", "PCB Motherboard", "Gearbox Core",
        "Wiring Harness", "Bearing Assembly", "Impeller Core", "Valve Block"
    ],
    SkuCategory.FINISHED_GOOD.value: [
        "Centrifugal Pump", "Power Inverter", "Control Unit", "Pneumatic Drill",
        "Turbine Generator", "Automated Sorter", "Pressure Regulator", "Laser Sensor"
    ],
}

SPECS = ["100A", "45mm", "Grade-A", "v2", "IP67", "Series-X", "High-Torque", "24V", "Rev-B", "Heavy-Load"]


def generate_skus(num_skus: int, rng: np.random.Generator, year: int = 2026) -> pd.DataFrame:
    """
    Generate deterministic master SKU records.
    - Categories: balanced supply chain distribution (Raw: 25%, Packaging: 15%, Subassembly: 30%, Finished: 30%)
    - Unit Costs: Lognormal distribution per category
    - Selling Price: Markup of 1.25x to 2.2x over unit cost
    - Lifecycle: 90% ACTIVE, 7% PHASE_OUT, 3% OBSOLETE
    """
    sku_ids = [build_sku_id(i + 1) for i in range(num_skus)]

    # Category distribution
    categories = [
        SkuCategory.RAW_MATERIAL.value,
        SkuCategory.PACKAGING.value,
        SkuCategory.SUBASSEMBLY.value,
        SkuCategory.FINISHED_GOOD.value,
    ]
    category_weights = [0.25, 0.15, 0.30, 0.30]
    cat_choices = [str(c) for c in rng.choice(categories, size=num_skus, p=category_weights)]

    # Unit of measure mapping based on category
    uom_choices = []
    for cat in cat_choices:
        if cat == SkuCategory.RAW_MATERIAL.value:
            uom = rng.choice(["KG", "L", "EA"], p=[0.5, 0.3, 0.2])
        elif cat == SkuCategory.PACKAGING.value:
            uom = rng.choice(["BOX", "PALLET", "EA"], p=[0.5, 0.3, 0.2])
        else:
            uom = "EA"
        uom_choices.append(str(uom))

    # Unit costs based on category (Raw materials $10-$50, Subassemblies $50-$200, Finished Goods $150-$800, Packaging $1-$15)
    mean_costs = {
        SkuCategory.RAW_MATERIAL.value: (3.2, 0.5),   # exp(3.2) ~= $24
        SkuCategory.PACKAGING.value: (1.5, 0.4),      # exp(1.5) ~= $4.5
        SkuCategory.SUBASSEMBLY.value: (4.6, 0.5),    # exp(4.6) ~= $100
        SkuCategory.FINISHED_GOOD.value: (5.7, 0.6),  # exp(5.7) ~= $300
    }

    unit_costs = np.zeros(num_skus, dtype=float)
    cat_choices_arr = np.array(cat_choices)
    for cat in categories:
        mask = (cat_choices_arr == cat)
        count = int(np.sum(mask))
        if count > 0:
            mu, sigma = mean_costs[cat]
            sampled_costs = np.round(rng.lognormal(mean=mu, sigma=sigma, size=count), 2)
            # Ensure minimum $0.50
            sampled_costs = np.maximum(sampled_costs, 0.50)
            unit_costs[mask] = sampled_costs

    # Selling prices: 1.25x - 2.2x of unit cost
    markups = rng.uniform(1.25, 2.20, size=num_skus)
    selling_prices = np.round(unit_costs * markups, 2)

    # Holding cost annual rate (typically 15% - 25% per year)
    holding_cost_rates = np.round(rng.uniform(0.15, 0.25, size=num_skus), 4)

    # Lifecycle status: 90% ACTIVE, 7% PHASE_OUT, 3% OBSOLETE
    lifecycle_statuses = [
        str(s) for s in rng.choice(
            [SkuLifecycle.ACTIVE.value, SkuLifecycle.PHASE_OUT.value, SkuLifecycle.OBSOLETE.value],
            size=num_skus,
            p=[0.90, 0.07, 0.03]
        )
    ]

    # Descriptive naming
    names = []
    for i in range(num_skus):
        cat = cat_choices[i]
        prefix = str(rng.choice(NAME_PREFIXES))
        noun = str(rng.choice(NOUNS_BY_CATEGORY[cat]))
        spec = str(rng.choice(SPECS))
        names.append(f"{prefix} {noun} {spec}")

    df = pd.DataFrame({
        "sku_id": sku_ids,
        "name": names,
        "category": cat_choices,
        "unit_of_measure": uom_choices,
        "unit_cost": unit_costs,
        "selling_price": selling_prices,
        "holding_cost_rate": holding_cost_rates,
        "lifecycle_status": lifecycle_statuses,
        "effective_start_date": f"{year}-01-01",
        "effective_end_date": f"{year}-12-31",
    })

    column_order = list(SKU.model_fields.keys())
    return validate_and_sort_dataframe(df, SKU, "sku_id", column_order)
