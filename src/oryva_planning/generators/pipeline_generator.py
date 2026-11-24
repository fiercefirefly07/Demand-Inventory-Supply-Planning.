"""
End-to-End Pipeline Data Generator for Oryva Planning.
Orchestrates master and dependent generators in strict dependency order:
Masters (SKU, Location, Supplier, Bridges) ->
Dependents (Demand, Inventory, Capacity, LeadTime, POs + Events, ProductionPlans)
Preserves determinism via SeedSequence.spawn().
"""

from pathlib import Path
from typing import Dict
import pandas as pd

from oryva_planning.config import PlanningConfig
from oryva_planning.generators.base import SeedStreamManager
from oryva_planning.generators.sku_generator import generate_skus
from oryva_planning.generators.location_generator import generate_locations
from oryva_planning.generators.supplier_generator import generate_suppliers
from oryva_planning.generators.bridge_generator import (
    generate_sku_suppliers,
    generate_sku_substitutes,
)
from oryva_planning.generators.demand_generator import generate_demand
from oryva_planning.generators.inventory_generator import generate_inventory
from oryva_planning.generators.capacity_leadtime_generator import generate_capacity_and_lead_times
from oryva_planning.generators.order_generator import generate_purchase_orders
from oryva_planning.generators.production_generator import generate_production_plans


def generate_all_datasets(
    config: PlanningConfig,
    save_to_disk: bool = True
) -> Dict[str, pd.DataFrame]:
    """
    Run complete synthetic data generator across master and dependent layers.
    Returns dictionary of validated, sorted DataFrames for all 10 core source tables.
    """
    stream_mgr = SeedStreamManager(config.seed)
    rngs = stream_mgr.spawn_generators([
        "sku",
        "location",
        "supplier",
        "sku_supplier",
        "sku_substitute",
        "demand",
        "inventory",
        "capacity_leadtime",
        "purchase_orders",
        "production_plan",
    ])

    # 1. Master entities
    sku_df = generate_skus(config.scale.num_skus, rngs["sku"], config.year)
    location_df = generate_locations(config.scale.num_locations, rngs["location"], config.year)
    supplier_df = generate_suppliers(config.scale.num_suppliers, rngs["supplier"], config.year)

    # 2. Relational Bridges
    sku_supplier_df = generate_sku_suppliers(
        sku_df, supplier_df, config.scale.avg_suppliers_per_sku, rngs["sku_supplier"], config.year
    )
    sku_substitute_df = generate_sku_substitutes(
        sku_df, config.scale.avg_substitutes_per_sku, rngs["sku_substitute"], config.year
    )

    # 3. Dependent Demand & Inventory
    demand_df = generate_demand(
        sku_df, location_df, config.planning_horizon_weeks, rngs["demand"], config.year
    )
    inventory_df = generate_inventory(
        sku_df, location_df, demand_df, rngs["inventory"], config.year
    )

    # 4. Sourcing Capacity & Lead Times
    capacity_df, lead_time_df = generate_capacity_and_lead_times(
        sku_supplier_df,
        supplier_df,
        location_df,
        demand_df,
        config.planning_horizon_weeks,
        rngs["capacity_leadtime"],
        config.year,
    )

    # 5. Purchase Orders & Lifecycle History Events
    po_df, po_event_df = generate_purchase_orders(
        config.scale.num_inbound_pos,
        sku_df,
        sku_supplier_df,
        supplier_df,
        lead_time_df,
        rngs["purchase_orders"],
        config.year,
    )

    # 6. Internal Production Plans
    production_df = generate_production_plans(
        sku_df,
        location_df,
        demand_df,
        config.planning_horizon_weeks,
        rngs["production_plan"],
        config.year,
    )

    datasets = {
        "sku": sku_df,
        "location": location_df,
        "supplier": supplier_df,
        "sku_supplier": sku_supplier_df,
        "sku_substitute": sku_substitute_df,
        "forecastdemand": demand_df,
        "inventory": inventory_df,
        "suppliercapacity": capacity_df,
        "leadtime": lead_time_df,
        "purchaseorder": po_df,
        "purchaseorderevent": po_event_df,
        "productionplan": production_df,
    }

    if save_to_disk:
        out_dir = Path(config.paths.input_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        for name, df in datasets.items():
            csv_path = out_dir / f"{name}.csv"
            df.to_csv(csv_path, index=False, lineterminator="\n", float_format="%.4f")

    return datasets
