"""
Tests for geoafrica.datasets.roads
"""
import pytest
from unittest.mock import patch
import geopandas as gpd
from shapely.geometry import LineString


@patch("geoafrica.datasets.roads.get_features")
def test_get_network(mock_features):
    from geoafrica.datasets.roads import get_network
    
    mock_features.return_value = gpd.GeoDataFrame(
        {"highway": ["primary"]},
        geometry=[LineString([(0, 0), (1, 1)])],
        crs="EPSG:4326"
    )

    gdf = get_network("Lagos")
    assert isinstance(gdf, gpd.GeoDataFrame)
    mock_features.assert_called_once()
    assert "highway" in gdf.columns


@patch("geoafrica.datasets.roads.get_network")
@patch("geoafrica.datasets.boundaries.get_admin")
def test_road_stats(mock_admin, mock_network):
    from geoafrica.datasets.roads import road_stats
    import pandas as pd
    from shapely.geometry import box

    mock_network.return_value = gpd.GeoDataFrame(
        {"highway": ["primary"]},
        geometry=[LineString([(0, 0), (1, 1)])],
        crs="EPSG:4326"
    )

    mock_admin.return_value = gpd.GeoDataFrame(
        {"name": ["Lagos"]}, geometry=[box(-1, -1, 2, 2)], crs="EPSG:4326"
    )

    df = road_stats("Nigeria", level=1)
    assert isinstance(df, pd.DataFrame)
    assert "road_length_km" in df.columns
    assert "road_density_km_per_km2" in df.columns
