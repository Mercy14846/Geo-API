"""
GeoAfrica — Analysis: Spatial Operations
==========================================
Merczcord Technologies Ltd.

Common spatial analysis helpers that complement the dataset modules.

Usage
-----
    from geoafrica.analysis import spatial

    clipped = spatial.clip(facilities, nigeria)
    buffered = spatial.buffer_km(hospitals, km=5)
    intersection = spatial.intersect(roads, flood_zones)
    dissolved = spatial.dissolve_by(districts, column="state")
"""

from __future__ import annotations

import geopandas as gpd
from shapely.geometry import box


def clip(
    gdf: gpd.GeoDataFrame,
    mask: gpd.GeoDataFrame | gpd.GeoSeries,
) -> gpd.GeoDataFrame:
    """
    Clip *gdf* to the extent of *mask*.

    Parameters
    ----------
    gdf : GeoDataFrame
        Input features to clip.
    mask : GeoDataFrame or GeoSeries
        Clipping boundary.

    Returns
    -------
    GeoDataFrame
    """
    if isinstance(mask, gpd.GeoDataFrame):
        mask = mask.geometry.union_all()
    elif isinstance(mask, gpd.GeoSeries):
        mask = mask.union_all()
    return gdf.clip(mask)


def buffer_km(
    gdf: gpd.GeoDataFrame,
    km: float,
    cap_style: int = 1,
) -> gpd.GeoDataFrame:
    """
    Buffer geometries by *km* kilometres.

    Automatically re-projects to an equal-area CRS, applies the buffer,
    then reprojects back to the original CRS.

    Parameters
    ----------
    gdf : GeoDataFrame
        Input features.
    km : float
        Buffer distance in kilometres.
    cap_style : int
        Buffer cap style (1=round, 2=flat, 3=square).

    Returns
    -------
    GeoDataFrame with buffered geometries.

    Examples
    --------
    >>> hospital_catchments = spatial.buffer_km(hospitals, km=10)
    """
    original_crs = gdf.crs
    gdf_proj = gdf.to_crs(epsg=6933)  # WGS 84 / Equal Earth Africa
    gdf_proj = gdf_proj.copy()
    gdf_proj.geometry = gdf_proj.geometry.buffer(km * 1000, cap_style=cap_style)
    return gdf_proj.to_crs(original_crs)


def intersect(
    gdf_a: gpd.GeoDataFrame,
    gdf_b: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    Return the geometric intersection of *gdf_a* and *gdf_b*.

    Parameters
    ----------
    gdf_a, gdf_b : GeoDataFrame
        Input feature sets.

    Returns
    -------
    GeoDataFrame of intersecting geometries.
    """
    if gdf_a.crs != gdf_b.crs:
        gdf_b = gdf_b.to_crs(gdf_a.crs)
    return gpd.overlay(gdf_a, gdf_b, how="intersection", keep_geom_type=False)


def dissolve_by(
    gdf: gpd.GeoDataFrame,
    column: str,
    aggfunc: str = "first",
) -> gpd.GeoDataFrame:
    """
    Dissolve features by a column value (merge polygons sharing the same attribute).

    Parameters
    ----------
    gdf : GeoDataFrame
        Input features.
    column : str
        Column to dissolve by.
    aggfunc : str
        Aggregation function for non-spatial columns.

    Returns
    -------
    GeoDataFrame

    Examples
    --------
    >>> nigeria_regions = spatial.dissolve_by(states, column="region")
    """
    return gdf.dissolve(by=column, aggfunc=aggfunc).reset_index()


def bbox_to_polygon(bbox: list[float]) -> gpd.GeoDataFrame:
    """
    Convert a bounding box to a single-row GeoDataFrame polygon.

    Parameters
    ----------
    bbox : list of float
        [min_lon, min_lat, max_lon, max_lat]

    Returns
    -------
    GeoDataFrame with one polygon geometry.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    return gpd.GeoDataFrame(
        geometry=[box(min_lon, min_lat, max_lon, max_lat)],
        crs="EPSG:4326",
    )


def within_distance(
    gdf: gpd.GeoDataFrame,
    point_lon: float,
    point_lat: float,
    km: float,
) -> gpd.GeoDataFrame:
    """
    Filter features within *km* kilometres of a point.

    Parameters
    ----------
    gdf : GeoDataFrame
        Input features.
    point_lon, point_lat : float
        Reference point coordinate.
    km : float
        Search radius in kilometres.

    Returns
    -------
    GeoDataFrame of features within the radius (with 'distance_km' column).
    """
    from shapely.geometry import Point

    gdf_proj = gdf.to_crs(epsg=6933)
    ref_proj = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy([point_lon], [point_lat]),
        crs="EPSG:4326",
    ).to_crs(epsg=6933)

    ref_x = ref_proj.geometry.x.iloc[0]
    ref_y = ref_proj.geometry.y.iloc[0]

    distances = gdf_proj.geometry.apply(lambda g: g.centroid.distance(Point(ref_x, ref_y)) / 1000)
    mask = distances <= km
    result = gdf[mask].copy()
    result["distance_km"] = distances[mask].values
    return result.sort_values("distance_km").reset_index(drop=True)


def simplify(
    gdf: gpd.GeoDataFrame,
    tolerance_km: float = 1.0,
) -> gpd.GeoDataFrame:
    """
    Simplify geometries to reduce file size.

    Parameters
    ----------
    gdf : GeoDataFrame
    tolerance_km : float
        Simplification tolerance in kilometres.

    Returns
    -------
    Simplified GeoDataFrame.
    """
    original_crs = gdf.crs
    gdf_proj = gdf.to_crs(epsg=6933)
    gdf_proj = gdf_proj.copy()
    gdf_proj.geometry = gdf_proj.geometry.simplify(tolerance_km * 1000, preserve_topology=True)
    return gdf_proj.to_crs(original_crs)
