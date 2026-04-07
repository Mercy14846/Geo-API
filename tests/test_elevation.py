"""
Tests for geoafrica.datasets.elevation
"""
import pytest
from unittest.mock import patch, MagicMock
import xarray as xr
import pandas as pd
import numpy as np


def test_list_sources():
    from geoafrica.datasets.elevation import list_sources
    df = list_sources()
    assert isinstance(df, pd.DataFrame)
    assert "code" in df.columns
    assert "SRTMGL1" in df["code"].values


@patch("geoafrica.datasets.boundaries.get_bbox")
@patch("geoafrica.core.config.GeoAfricaConfig.get_api_key")
@patch("geoafrica.datasets.elevation.GeoAfricaSession")
def test_get_dem_calls_opentopo(mock_session, mock_key, mock_bbox):
    from geoafrica.datasets.elevation import get_dem
    
    mock_bbox.return_value = [3.0, 4.0, 15.0, 13.0]
    mock_key.return_value = "fake_key"
    mock_resp = MagicMock()
    mock_resp.content = b"fake tif content"
    mock_resp.status_code = 200
    mock_session.return_value.__enter__.return_value.get.return_value = mock_resp

    with patch("xarray.open_dataarray") as mock_xr:
        mock_xr.return_value = xr.DataArray(np.zeros((10, 10)))
        
        # Calling get_dem should succeed if rasterio/xarray mock works
        da = get_dem("Nigeria")
        assert isinstance(da, xr.DataArray)


def test_terrain_profile():
    from geoafrica.datasets.elevation import terrain_profile
    import pandas as pd

    with patch("xarray.open_dataarray") as mock_xr, \
         patch("geoafrica.datasets.elevation.get_dem_bbox") as mock_fetch:

        # Mock raster value selection points
        fake_da = xr.DataArray(np.zeros((10, 10)))
        mock_fetch.return_value = fake_da

        # Mocking the sample() call to trace profile
        with patch("xarray.DataArray.sel", side_effect=lambda **kwargs: xr.DataArray(50.0)):
            df = terrain_profile((3.0, 6.0), (3.1, 6.1), num_points=10)
            
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 10
            assert "elevation_m" in df.columns
            assert "distance_km" in df.columns


def test_compute_slope_aspect():
    from geoafrica.datasets.elevation import compute_slope_aspect
    
    # Create fake DEM
    arr = np.array([
        [10, 10, 10],
        [10, 15, 10],
        [10, 10, 10]
    ], dtype=float)
    
    da = xr.DataArray(
        arr,
        dims=("y", "x"),
        coords={"y": [2.0, 1.0, 0.0], "x": [0.0, 1.0, 2.0]}
    )
    
    with patch("xarray.DataArray.rio", create=True) as mock_rio:
        mock_rio.resolution.return_value = (30, 30)
        slope, aspect = compute_slope_aspect(da)
        assert isinstance(slope, xr.DataArray)
        assert isinstance(aspect, xr.DataArray)
