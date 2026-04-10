"""
GeoAfrica — I/O: Universal Readers
=====================================
Merczcord Technologies Ltd.

Read geospatial files from local disk or remote URLs.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import xarray

SUPPORTED_VECTOR_FORMATS = [".geojson", ".json", ".shp", ".gpkg", ".kml", ".fgb", ".parquet"]
SUPPORTED_RASTER_FORMATS = [".tif", ".tiff", ".nc", ".nc4", ".hdf", ".h5"]


def read(
    path_or_url: str | Path,
    layer: str | None = None,
    crs: str = "EPSG:4326",
) -> "gpd.GeoDataFrame | xarray.DataArray":
    """
    Universal reader — loads vector or raster data from a local path or URL.

    Supports: GeoJSON, Shapefile, GeoPackage, GeoParquet, KML, FlatGeobuf,
              COG/GeoTIFF, NetCDF, HDF5.

    Parameters
    ----------
    path_or_url : str or Path
        File path or HTTP/S3 URL.
    layer : str, optional
        Layer name (for GeoPackage or multi-layer files).
    crs : str
        Output CRS. Default EPSG:4326.

    Returns
    -------
    GeoDataFrame (for vector) or xarray.DataArray (for raster).

    Examples
    --------
    >>> gdf = read("nigeria_states.geojson")
    >>> gdf = read("s3://my-bucket/data.gpkg", layer="roads")
    >>> dem = read("https://example.com/dem.tif")
    """
    path = str(path_or_url)
    ext = Path(path.split("?")[0]).suffix.lower()

    if ext in SUPPORTED_RASTER_FORMATS or ext in (".tif", ".tiff"):
        return _read_raster(path)
    else:
        return _read_vector(path, layer=layer, crs=crs)


def _read_vector(path: str, layer: str | None, crs: str) -> gpd.GeoDataFrame:
    kwargs = {}
    if layer:
        kwargs["layer"] = layer

    # Handle GeoParquet
    if path.endswith(".parquet"):
        try:
            gdf = gpd.read_parquet(path)
        except Exception:
            raise ValueError(f"Could not read GeoParquet file: {path}")
    else:
        gdf = gpd.read_file(path, **kwargs)

    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    return gdf.to_crs(crs)


def _read_raster(path: str) -> "xarray.DataArray":
    try:
        import rioxarray  # noqa: F401
        import xarray as xr
    except ImportError:
        raise ImportError("Install: pip install rioxarray xarray rasterio")

    da = xr.open_dataarray(path, engine="rasterio")
    if da.rio.crs is None:
        da = da.rio.write_crs("EPSG:4326")
    return da


def read_csv_geo(
    path: str | Path,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    crs: str = "EPSG:4326",
) -> gpd.GeoDataFrame:
    """
    Read a CSV with lat/lon columns and convert to a point GeoDataFrame.

    Parameters
    ----------
    path : str or Path
        Path to CSV file.
    lat_col, lon_col : str
        Column names for latitude and longitude.
    crs : str
        Output CRS.

    Returns
    -------
    GeoDataFrame with Point geometries.
    """
    import pandas as pd
    df = pd.read_csv(path)
    if lat_col not in df.columns or lon_col not in df.columns:
        raise ValueError(f"Columns '{lat_col}' and '{lon_col}' not found in CSV.")
    return gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
        crs=crs,
    )
