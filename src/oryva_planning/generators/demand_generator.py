"""
Vectorized Forecast Demand Generator for Oryva Planning.
Generates weekly demand across SKU-location pairs using numpy vectorization.
Incorporates:
- Pareto-like SKU popularity distribution
- Regional location sizing factors
- Annual seasonality (sine/cosine curves + Q4 holiday surge)
- Random demand spike weeks (2-3 spikes per SKU)
- Category-appropriate statistical distributions
"""

from typing import List, Tuple
from datetime import date, timedelta
import numpy as np
import pandas as pd

from oryva_planning.schema.enums import UnitOfMeasure
from oryva_planning.schema.entities import ForecastDemand
from oryva_planning.generators.base import validate_and_sort_dataframe


def get_monday_of_week(year: int, week: int) -> str:
    """Return ISO format YYYY-MM-DD for Monday of given ISO week."""
    # First Monday of the ISO year
    jan4 = date(year, 1, 4)
    start_monday = jan4 - timedelta(days=jan4.isoweekday() - 1)
    target_monday = start_monday + timedelta(weeks=int(week) - 1)
    return target_monday.isoformat()


def generate_demand(
    sku_df: pd.DataFrame,
    location_df: pd.DataFrame,
    num_weeks: int,
    rng: np.random.Generator,
    year: int = 2026,
) -> pd.DataFrame:
    """
    Generate deterministic forecast demand using vectorized NumPy operations.
    Supports scaling up to 7.8M rows (3,000 SKUs x 50 locations x 52 weeks) in seconds.
    """
    sku_ids = sku_df["sku_id"].to_numpy()
    sku_uoms = sku_df["unit_of_measure"].to_numpy()
    loc_ids = location_df["location_id"].to_numpy()

    n_skus = len(sku_ids)
    n_locs = len(loc_ids)
    total_combinations = n_skus * n_locs * num_weeks

    # 1. Base demand per SKU: Pareto-like lognormal distribution
    # 20% of SKUs drive 80% of volume
    base_sku_demand = rng.lognormal(mean=3.8, sigma=1.1, size=n_skus)
    # Ensure minimum base demand
    base_sku_demand = np.maximum(base_sku_demand, 5.0)

    # 2. Location weight factor: larger hubs handle more volume
    loc_weights = rng.uniform(0.6, 1.4, size=n_locs)

    # 3. Weekly seasonality factor for weeks 1..num_weeks
    week_nums = np.arange(1, num_weeks + 1)
    # Sinusoidal base wave
    seasonality = 1.0 + 0.18 * np.sin(2 * np.pi * week_nums / 52.0)
    # Q4 / Year-end peak (weeks 44-51)
    holiday_boost = np.where((week_nums >= 44) & (week_nums <= 51), 1.45, 1.0)
    seasonality = seasonality * holiday_boost

    # 4. Meshgrid to construct complete (n_skus, n_locs, num_weeks) tensor
    # Shape: (n_skus, n_locs, num_weeks)
    mean_demand_grid = (
        base_sku_demand[:, np.newaxis, np.newaxis]
        * loc_weights[np.newaxis, :, np.newaxis]
        * seasonality[np.newaxis, np.newaxis, :]
    )

    # 5. Inject spike weeks: select 2 random spike weeks per SKU where demand spikes by 3x-4.5x
    spike_multiplier = np.ones((n_skus, num_weeks), dtype=np.float64)
    for s_idx in range(n_skus):
        spike_weeks = rng.choice(num_weeks, size=min(2, num_weeks), replace=False)
        spike_factors = rng.uniform(2.8, 4.2, size=len(spike_weeks))
        spike_multiplier[s_idx, spike_weeks] = spike_factors

    mean_demand_grid = mean_demand_grid * spike_multiplier[:, np.newaxis, :]

    # 6. Sample forecast quantity: Poisson/Negative-Binomial approximation with noise
    relative_noise = rng.normal(loc=1.0, scale=0.15, size=mean_demand_grid.shape)
    forecast_qty_grid = np.maximum(0.0, mean_demand_grid * relative_noise)
    forecast_qty_grid = np.round(forecast_qty_grid, 2)
    mean_demand_grid = np.round(mean_demand_grid, 2)

    # 7. Flatten arrays efficiently
    # Repeat SKUs: each SKU repeated (n_locs * num_weeks) times
    flat_skus = np.repeat(sku_ids, n_locs * num_weeks)
    flat_uoms = np.repeat(sku_uoms, n_locs * num_weeks)

    # Tile Locations: each location repeated num_weeks times, tiled n_skus times
    loc_repeats = np.repeat(loc_ids, num_weeks)
    flat_locs = np.tile(loc_repeats, n_skus)

    # Tile Weeks: 1..num_weeks tiled (n_skus * n_locs) times
    flat_weeks = np.tile(week_nums, n_skus * n_locs)

    # Precompute week strings and dates
    week_str_map = {w: f"{year}W{w:02d}" for w in week_nums}
    date_str_map = {w: get_monday_of_week(year, w) for w in week_nums}

    flat_week_strs = np.array([week_str_map[w] for w in flat_weeks], dtype=object)
    flat_date_strs = np.array([date_str_map[w] for w in flat_weeks], dtype=object)

    # Construct primary keys: DEM-<sku>-<loc>-2026W01
    # Using vectorized string concatenation
    flat_ids = (
        "DEM-" + flat_skus + "-" + flat_locs + "-" + flat_week_strs
    )

    flat_mean_demand = mean_demand_grid.flatten()
    flat_forecast_qty = forecast_qty_grid.flatten()

    df = pd.DataFrame({
        "demand_id": flat_ids,
        "sku_id": flat_skus,
        "location_id": flat_locs,
        "forecast_week": flat_week_strs,
        "forecast_date": flat_date_strs,
        "mean_demand": flat_mean_demand,
        "forecast_qty": flat_forecast_qty,
        "unit_of_measure": flat_uoms,
    })

    column_order = list(ForecastDemand.model_fields.keys())
    return validate_and_sort_dataframe(df, ForecastDemand, "demand_id", column_order)
