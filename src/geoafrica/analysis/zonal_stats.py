"""
GeoAfrica — Zonal Statistics Module
======================================
Merczcord Technologies Ltd.

Compute raster statistics (mean, sum, max, etc.) within vector zones.

Usage
-----
    from geoafrica.analysis import zonal_stats

    # Mean population per state
    stats = zonal_stats.compute(pop_raster, nigeria_states, stats=["mean","sum","max"])

    # Overlay rainfall on districts
    rain_stats = zonal_stats.compute(chirps_da, districts)
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import xarray

VALID_STATS = ["mean", "sum", "min", "max", "std", "count", "median", "range"]


def compute(
    raster: xarray.DataArray,
    zones: gpd.GeoDataFrame,
    stats: list[str] | None = None,
    nodata: float = -9999,
    zone_label_col: str | None = None,
) -> pd.DataFrame:
    """
    Compute statistics of *raster* values within each polygon in *zones*.

    Parameters
    ----------
    raster : xarray.DataArray
        Input raster (e.g. from population.get_grid() or climate.get_rainfall()).
    zones : GeoDataFrame
        Polygon zones (e.g. admin boundaries).
    stats : list of str, optional
        Statistics to compute. Options: mean, sum, min, max, std, count,
        median, range. Default: ['mean', 'sum', 'max'].
    nodata : float
        Value to treat as nodata (masked out). Default -9999.
    zone_label_col : str, optional
        Column in *zones* to use as label. Auto-detected if None.

    Returns
    -------
    DataFrame with one row per zone and one column per statistic.

    Examples
    --------
    >>> stats = zonal_stats.compute(pop_grid, states, stats=["sum","mean"])
    >>> stats.head()
    """
    if stats is None:
        stats = ["mean", "sum", "max"]

    for s in stats:
        if s not in VALID_STATS:
            raise ValueError(f"Unknown stat '{s}'. Valid: {VALID_STATS}")

    # Auto-detect zone label column
    if zone_label_col is None:
        name_candidates = [c for c in zones.columns if "name" in c.lower() and c != "geometry"]
        zone_label_col = name_candidates[0] if name_candidates else zones.columns[0]

    # Ensure matching CRS
    raster_crs = raster.rio.crs if hasattr(raster, "rio") else None
    if raster_crs:
        zones = zones.to_crs(str(raster_crs))
    else:
        zones = zones.to_crs("EPSG:4326")

    records = []
    for _, row in zones.iterrows():
        try:
            clipped = raster.rio.clip([row.geometry], all_touched=True, drop=True)
            values = clipped.values.flatten().astype(float)
            values = values[(values > nodata) & (~np.isnan(values))]
        except Exception:
            values = np.array([])

        stat_vals = {"zone": row[zone_label_col]}
        for stat in stats:
            if len(values) == 0:
                stat_vals[stat] = float("nan")
            elif stat == "mean":
                stat_vals[stat] = float(np.mean(values))
            elif stat == "sum":
                stat_vals[stat] = float(np.sum(values))
            elif stat == "min":
                stat_vals[stat] = float(np.min(values))
            elif stat == "max":
                stat_vals[stat] = float(np.max(values))
            elif stat == "std":
                stat_vals[stat] = float(np.std(values))
            elif stat == "count":
                stat_vals[stat] = int(len(values))
            elif stat == "median":
                stat_vals[stat] = float(np.median(values))
            elif stat == "range":
                stat_vals[stat] = float(np.max(values) - np.min(values))

        records.append(stat_vals)

    df = pd.DataFrame(records)
    # Round numeric columns
    for stat in stats:
        if stat in df.columns and stat != "count":
            df[stat] = df[stat].round(4)
    return df
