"""
Tests for geoafrica.datasets.health
"""
import pytest
from unittest.mock import patch, MagicMock
import geopandas as gpd


# Mock healthsites response
MOCK_FEATURES = {
    "results": [
        {
            "name": "Lagos Health",
            "facility_type": "hospital",
            "location": {"coordinates": [3.38, 6.45]}
        }
    ]
}

@patch("geoafrica.datasets.boundaries.get_bbox")
@patch("geoafrica.datasets.health.GeoAfricaSession")
def test_get_facilities(mock_session, mock_get_bbox):
    from geoafrica.datasets.health import get_facilities
    
    mock_get_bbox.return_value = [2.0, 4.0, 14.0, 13.0]
    
    mock_resp = MagicMock()
    mock_resp.json.return_value = MOCK_FEATURES
    mock_session.return_value.__enter__.return_value._session.get.return_value = mock_resp

    gdf = get_facilities("Nigeria", facility_type="hospital")
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert len(gdf) == 1
    assert "name" in gdf.columns


@patch("geoafrica.datasets.health.get_facilities")
@patch("geoafrica.analysis.proximity.nearest_facility")
def test_nearest_to(mock_nearest, mock_facilities):
    from geoafrica.datasets.health import nearest_to
    
    # Mocking get_facilities
    mock_facilities.return_value = gpd.GeoDataFrame(
        {"name": ["Other Facility"]},
        geometry=gpd.points_from_xy([3.4], [6.5]),
        crs="EPSG:4326"
    )
    
    # Mocking nearest_facility
    mock_nearest.return_value = gpd.GeoDataFrame(
        {"nearest_name": ["Lagos Health"], "nearest_distance_km": [2.5]},
        geometry=gpd.points_from_xy([3.38], [6.45]),
        crs="EPSG:4326"
    )

    result = nearest_to(6.45, 3.38, "Nigeria")
    assert isinstance(result, gpd.GeoDataFrame)
    assert len(result) == 1
    assert result.iloc[0]["name"] == "Other Facility"


@patch("geoafrica.datasets.health.get_facilities")
@patch("geoafrica.datasets.boundaries.get_admin")
def test_count_by_admin(mock_boundaries, mock_facilities):
    from geoafrica.datasets.health import count_by_admin
    import pandas as pd
    from shapely.geometry import Point, box

    # Fake boundaries
    mock_boundaries.return_value = gpd.GeoDataFrame(
        {"name": ["Lagos"]}, geometry=[box(3.0, 6.0, 4.0, 7.0)], crs="EPSG:4326"
    )

    # Fake facilities within boundary
    mock_facilities.return_value = gpd.GeoDataFrame(
        {"name": ["Lagos Health"]}, geometry=[Point(3.5, 6.5)], crs="EPSG:4326"
    )

    df = count_by_admin("Nigeria")
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "facility_count" in df.columns
    assert df["facility_count"].iloc[0] == 1
