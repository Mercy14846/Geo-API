"""
GeoAfrica — I/O: Writers
===========================
Merczcord Technologies Ltd.

Export GeoDataFrames to common formats.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import geopandas as gpd
import pandas as pd


def to_geojson(gdf: gpd.GeoDataFrame, path: Union[str, Path], indent: int = 2) -> str:
    """Save GeoDataFrame to GeoJSON. Returns path."""
    path = str(path)
    gdf.to_crs("EPSG:4326").to_file(path, driver="GeoJSON")
    return path


def to_shapefile(gdf: gpd.GeoDataFrame, path: Union[str, Path]) -> str:
    """Save GeoDataFrame to Shapefile (.shp). Returns path."""
    path = str(path)
    if not path.endswith(".shp"):
        path += ".shp"
    gdf.to_file(path)
    return path


def to_geopackage(
    gdf: gpd.GeoDataFrame,
    path: Union[str, Path],
    layer: str = "data",
) -> str:
    """Save GeoDataFrame to GeoPackage (.gpkg). Returns path."""
    path = str(path)
    if not path.endswith(".gpkg"):
        path += ".gpkg"
    gdf.to_file(path, driver="GPKG", layer=layer)
    return path


def to_csv(
    gdf: gpd.GeoDataFrame,
    path: Union[str, Path],
    include_geometry: bool = True,
) -> str:
    """
    Save GeoDataFrame to CSV.

    Parameters
    ----------
    include_geometry : bool
        If True, adds 'latitude' and 'longitude' columns from point geometry,
        or 'wkt' column for other geometry types.
    """
    path = str(path)
    df = gdf.copy()
    if include_geometry:
        geom_type = gdf.geometry.geom_type.iloc[0] if not gdf.empty else "Polygon"
        if "Point" in geom_type:
            df["longitude"] = gdf.geometry.x
            df["latitude"] = gdf.geometry.y
        else:
            df["wkt"] = gdf.geometry.apply(lambda g: g.wkt)
    df = df.drop(columns=["geometry"], errors="ignore")
    df.to_csv(path, index=False)
    return path


def to_geoparquet(gdf: gpd.GeoDataFrame, path: Union[str, Path]) -> str:
    """Save GeoDataFrame to GeoParquet (.parquet). Returns path."""
    path = str(path)
    if not path.endswith(".parquet"):
        path += ".parquet"
    gdf.to_parquet(path)
    return path


def to_kml(gdf: gpd.GeoDataFrame, path: Union[str, Path]) -> str:
    """Save GeoDataFrame to KML. Returns path."""
    path = str(path)
    gdf.to_crs("EPSG:4326").to_file(path, driver="KML")
    return path
