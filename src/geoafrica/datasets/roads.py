"""
GeoAfrica — Roads Module
==========================
Merczcord Technologies Ltd.

Access road network data from OpenStreetMap for any country or region.

Usage
-----
    from geoafrica import roads

    # All primary roads in Nigeria
    ng_roads = roads.get_network("Nigeria", road_types=["primary","secondary"])

    # Road length statistics by admin area
    stats = roads.road_stats("Ghana", level=1)
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from geoafrica.datasets.osm import ROAD_TYPES, get_features


def get_network(
    location: str,
    road_types: list[str] | None = None,
    timeout: int = 180,
) -> gpd.GeoDataFrame:
    """
    Fetch road network from OSM for a location.

    Parameters
    ----------
    location : str
        Country or city name.
    road_types : list of str, optional
        OSM highway types. If None, returns primary + secondary roads.
        Options: motorway, trunk, primary, secondary, tertiary, residential.
    timeout : int
        Overpass query timeout.

    Returns
    -------
    GeoDataFrame with LineString geometries.

    Examples
    --------
    >>> roads_gdf = roads.get_network("Ethiopia", road_types=["primary", "trunk"])
    """
    if road_types is None:
        road_types = ["motorway", "trunk", "primary", "secondary"]

    for rt in road_types:
        if rt not in ROAD_TYPES:
            raise ValueError(f"Invalid road_type '{rt}'. Choose from: {ROAD_TYPES}")

    return get_features(
        location,
        tags={"highway": road_types},
        geometry_types=["way"],
        timeout=timeout,
    )


def road_stats(
    country: str,
    level: int = 1,
    road_types: list[str] | None = None,
) -> pd.DataFrame:
    """
    Compute road length (km) per administrative unit.

    Parameters
    ----------
    country : str
        Country name or ISO code.
    level : int
        Admin level (1=state, 2=district).
    road_types : list of str, optional
        Road type filter.

    Returns
    -------
    DataFrame with: admin_name, road_length_km, road_density_km_per_km2
    """
    from geoafrica.datasets.boundaries import get_admin

    roads_gdf = get_network(country, road_types=road_types)
    boundaries = get_admin(country, level=level)

    if roads_gdf.empty:
        return pd.DataFrame(columns=["admin_name", "road_length_km"])

    # Project to equal-area CRS for length measurement
    roads_proj = roads_gdf.to_crs(epsg=6933)
    boundaries_proj = boundaries.to_crs(epsg=6933)

    # Find name column
    name_cols = [c for c in boundaries.columns if "name" in c.lower() and c != "geometry"]
    name_col = name_cols[0] if name_cols else boundaries.columns[0]

    records = []
    for _, admin_row in boundaries_proj.iterrows():
        clipped = roads_proj.clip(admin_row.geometry)
        length_km = clipped.geometry.length.sum() / 1000
        area_km2 = admin_row.geometry.area / 1e6
        records.append({
            "admin_name": admin_row.get(name_col, ""),
            "road_length_km": round(length_km, 2),
            "area_km2": round(area_km2, 2),
            "road_density_km_per_km2": round(length_km / area_km2, 4) if area_km2 > 0 else 0,
        })

    return pd.DataFrame(records).sort_values("road_length_km", ascending=False).reset_index(drop=True)
