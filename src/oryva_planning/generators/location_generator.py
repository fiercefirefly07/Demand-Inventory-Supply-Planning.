"""
Synthetic Location Master Data Generator.
Generates facility network comprising Central Hubs, Regional DCs,
Manufacturing Plants, and Satellite Warehouses across global regions.
"""

from typing import List
import numpy as np
import pandas as pd

from oryva_planning.schema.enums import LocationType
from oryva_planning.schema.id_builders import build_location_id
from oryva_planning.schema.entities import Location
from oryva_planning.generators.base import validate_and_sort_dataframe

CITIES = [
    ("Chicago", "North America - Midwest"),
    ("Dallas", "North America - South"),
    ("Atlanta", "North America - Southeast"),
    ("Los Angeles", "North America - West"),
    ("Memphis", "North America - Central"),
    ("Newark", "North America - East"),
    ("Seattle", "North America - Northwest"),
    ("Rotterdam", "Europe - West"),
    ("Frankfurt", "Europe - Central"),
    ("Antwerp", "Europe - North"),
    ("Milan", "Europe - South"),
    ("Singapore", "Asia - Southeast"),
    ("Tokyo", "Asia - East"),
    ("Shanghai", "Asia - East"),
    ("Incheon", "Asia - East"),
    ("Sydney", "Oceania"),
    ("São Paulo", "Latin America"),
    ("Monterrey", "Latin America - North"),
    ("Dubai", "Middle East"),
    ("Johannesburg", "Africa - South"),
]

FACILITY_TYPE_SUFFIXES = {
    LocationType.CENTRAL_HUB.value: "Global Distribution Hub",
    LocationType.REGIONAL_DC.value: "Regional Fulfillment Center",
    LocationType.MANUFACTURING_PLANT.value: "Assembly & Production Plant",
    LocationType.SATELLITE_WH.value: "Satellite Transit Warehouse",
}


def generate_locations(num_locations: int, rng: np.random.Generator, year: int = 2026) -> pd.DataFrame:
    """
    Generate deterministic master Location records.
    - Types: 20% CENTRAL_HUB, 40% REGIONAL_DC, 20% MANUFACTURING_PLANT, 20% SATELLITE_WH
    - Holding costs: $0.01 - $0.08 per unit-day depending on facility type
    - Storage Capacity: 150,000 to 2,000,000 units
    """
    location_ids = [build_location_id(i + 1) for i in range(num_locations)]

    types = [
        LocationType.CENTRAL_HUB.value,
        LocationType.REGIONAL_DC.value,
        LocationType.MANUFACTURING_PLANT.value,
        LocationType.SATELLITE_WH.value,
    ]
    type_weights = [0.20, 0.40, 0.20, 0.20]
    loc_types = [str(t) for t in rng.choice(types, size=num_locations, p=type_weights)]

    names = []
    regions = []
    holding_costs = []
    capacities = []

    for i in range(num_locations):
        city, region = CITIES[i % len(CITIES)]
        loc_type = loc_types[i]
        suffix = FACILITY_TYPE_SUFFIXES[loc_type]

        # For multiple facilities in same city, append district / number
        facility_num = (i // len(CITIES)) + 1
        num_tag = f" #{facility_num}" if facility_num > 1 else ""
        name = f"{city} {suffix}{num_tag}"

        names.append(name)
        regions.append(region)

        # Holding cost per unit-day ($0.02 - $0.08)
        if loc_type == LocationType.CENTRAL_HUB.value:
            cost = rng.uniform(0.02, 0.04)
            cap = rng.integers(1_000_000, 2_500_000)
        elif loc_type == LocationType.REGIONAL_DC.value:
            cost = rng.uniform(0.03, 0.05)
            cap = rng.integers(500_000, 1_200_000)
        elif loc_type == LocationType.MANUFACTURING_PLANT.value:
            cost = rng.uniform(0.01, 0.03)
            cap = rng.integers(300_000, 800_000)
        else:  # SATELLITE_WH
            cost = rng.uniform(0.04, 0.07)
            cap = rng.integers(100_000, 400_000)

        holding_costs.append(round(float(cost), 4))
        capacities.append(int(cap))

    # All active initially (98% active, 2% scheduled inactive)
    is_active = [bool(a) for a in rng.choice([True, False], size=num_locations, p=[0.98, 0.02])]
    # Ensure at least first 5 locations are active
    for k in range(min(5, num_locations)):
        is_active[k] = True

    df = pd.DataFrame({
        "location_id": location_ids,
        "name": names,
        "type": loc_types,
        "region": regions,
        "holding_cost_per_unit_day": holding_costs,
        "capacity_units": capacities,
        "is_active": is_active,
        "effective_start_date": f"{year}-01-01",
        "effective_end_date": f"{year}-12-31",
    })

    column_order = list(Location.model_fields.keys())
    return validate_and_sort_dataframe(df, Location, "location_id", column_order)
