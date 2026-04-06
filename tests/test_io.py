"""
Tests for geoafrica.io
"""
import pytest
import geopandas as gpd
import xarray as xr
import numpy as np
from shapely.geometry import Point


def test_write_and_read_vector(tmp_path):
    from geoafrica.io.writers import to_geojson
    from geoafrica.io.readers import read

    gdf = gpd.GeoDataFrame(
        {"col1": [1, 2]},
        geometry=[Point(0, 0), Point(1, 1)],
        crs="EPSG:4326"
    )

    path = tmp_path / "test.geojson"
    to_geojson(gdf, path)

    assert path.exists()

    loaded = read(path)
    assert isinstance(loaded, gpd.GeoDataFrame)
    assert len(loaded) == 2


def test_write_and_read_csv(tmp_path):
    from geoafrica.io.writers import to_csv
    from geoafrica.io.readers import read_csv_geo

    gdf = gpd.GeoDataFrame(
        {"col1": ["a", "b"]},
        geometry=[Point(0, 0), Point(1, 1)],
        crs="EPSG:4326"
    )

    path = tmp_path / "test.csv"
    to_csv(gdf, path, include_geometry=True)
    assert path.exists()

    loaded = read_csv_geo(path, lon_col="longitude", lat_col="latitude")
    assert isinstance(loaded, gpd.GeoDataFrame)
    assert len(loaded) == 2
