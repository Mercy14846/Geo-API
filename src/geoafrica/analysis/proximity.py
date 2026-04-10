"""
GeoAfrica — Analysis: Proximity & Accessibility
=================================================
Merczcord Technologies Ltd.

Accessibility and proximity analysis — find nearest facilities,
service coverage, and catchment areas.

Usage
-----
    from geoafrica.analysis import proximity

    # Nearest hospital to each village centroid
    result = proximity.nearest_facility(villages, hospitals)

    # Coverage: population within 5km of a health facility
    coverage = proximity.service_coverage(facilities, population_grid, radius_km=5)
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd


def nearest_facility(
    origins: gpd.GeoDataFrame,
    facilities: gpd.GeoDataFrame,
    origin_label: str | None = None,
    facility_label: str | None = None,
    n: int = 1,
) -> gpd.GeoDataFrame:
    """
    For each origin, find the *n* nearest facilities (straight-line / Haversine).

    Parameters
    ----------
    origins : GeoDataFrame
        Points of interest (e.g. villages, community centres).
    facilities : GeoDataFrame
        Facility locations (e.g. hospitals, schools).
    origin_label : str, optional
        Column name in *origins* to use as label.
    facility_label : str, optional
        Column name in *facilities* to use as label.
    n : int
        Number of nearest facilities per origin. Default 1.

    Returns
    -------
    GeoDataFrame with origins + columns:
      nearest_name, nearest_distance_km (for n=1),
      or nearest_1_name/distance, nearest_2_name/distance, ... for n>1.

    Examples
    --------
    >>> result = proximity.nearest_facility(villages, hospitals)
    >>> result[["village", "nearest_name", "nearest_distance_km"]].head()
    """
    if origin_label is None:
        name_cols = [c for c in origins.columns if "name" in c.lower() and c != "geometry"]
        origin_label = name_cols[0] if name_cols else origins.columns[0]

    if facility_label is None:
        name_cols = [c for c in facilities.columns if "name" in c.lower() and c != "geometry"]
        facility_label = name_cols[0] if name_cols else facilities.columns[0]

    # Project both to equal-area for accurate distance
    origins_proj = origins.to_crs(epsg=6933)
    fac_proj = facilities.to_crs(epsg=6933)

    fac_centroids = fac_proj.geometry.centroid

    results = []
    for idx, row in origins_proj.iterrows():
        origin_centroid = row.geometry.centroid
        distances = fac_centroids.apply(
            lambda g: origin_centroid.distance(g) / 1000  # km
        )
        nearest_indices = distances.nsmallest(n).index.tolist()
        nearest_dists = distances[nearest_indices].tolist()

        row_data = dict(origins.loc[idx])
        for rank, (ni, dist) in enumerate(zip(nearest_indices, nearest_dists), start=1):
            suffix = "" if n == 1 else f"_{rank}"
            row_data[f"nearest{suffix}_name"] = facilities.loc[ni, facility_label] if facility_label in facilities.columns else str(ni)
            row_data[f"nearest{suffix}_distance_km"] = round(dist, 3)

        results.append(row_data)

    result_df = pd.DataFrame(results)
    return gpd.GeoDataFrame(result_df, geometry="geometry", crs=origins.crs)


def service_coverage(
    facilities: gpd.GeoDataFrame,
    population_raster: xarray.DataArray,
    radius_km: float = 5.0,
) -> dict:
    """
    Estimate population within *radius_km* of any facility.

    Parameters
    ----------
    facilities : GeoDataFrame
        Facility point locations.
    population_raster : xarray.DataArray
        Population grid (e.g. from population.get_grid()).
    radius_km : float
        Service radius in kilometres.

    Returns
    -------
    dict with keys:
      total_population, served_population, coverage_pct, unserved_population
    """
    from geoafrica.analysis.spatial import buffer_km

    catchments = buffer_km(facilities, km=radius_km)
    union = catchments.geometry.union_all()
    union_gdf = gpd.GeoDataFrame(geometry=[union], crs=facilities.crs)

    # Total population in raster extent
    total_pop = float(population_raster.where(population_raster > 0).sum().values)

    # Population within catchment
    try:
        clipped = population_raster.rio.clip(union_gdf.geometry, union_gdf.crs, drop=True)
        served_pop = float(clipped.where(clipped > 0).sum().values)
    except Exception:
        served_pop = 0.0

    coverage_pct = (served_pop / total_pop * 100) if total_pop > 0 else 0.0

    return {
        "total_population": int(total_pop),
        "served_population": int(served_pop),
        "unserved_population": int(total_pop - served_pop),
        "coverage_pct": round(coverage_pct, 2),
        "radius_km": radius_km,
    }


def point_in_polygon(
    points: gpd.GeoDataFrame,
    polygons: gpd.GeoDataFrame,
    how: str = "left",
) -> gpd.GeoDataFrame:
    """
    Spatial join: assign each point the attributes of the containing polygon.

    Parameters
    ----------
    points : GeoDataFrame
        Point features.
    polygons : GeoDataFrame
        Polygon features (e.g. admin boundaries).
    how : str
        Join type: 'left', 'inner'.

    Returns
    -------
    GeoDataFrame with combined attributes.
    """
    if points.crs != polygons.crs:
        polygons = polygons.to_crs(points.crs)
    return gpd.sjoin(points, polygons, how=how, predicate="within").reset_index(drop=True)
