"""
Tests for geoafrica.datasets.climate
"""
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import xarray as xr
import numpy as np


@patch("geoafrica.datasets.boundaries.get_country")
@patch("geoafrica.datasets.climate._download_chirps")
@patch("xarray.open_dataarray")
def test_get_rainfall(mock_xr, mock_download, mock_country):
    from geoafrica.datasets.climate import get_rainfall
    import rioxarray
    import geopandas as gpd
    from shapely.geometry import box
    
    mock_download.return_value = "fake_path.tif"
    mock_country.return_value = gpd.GeoDataFrame(geometry=[box(0, 0, 10, 10)], crs="EPSG:4326")
    
    fake_da = xr.DataArray(np.zeros((1, 10, 10)), dims=["time", "y", "x"])
    fake_da = fake_da.rio.write_crs("EPSG:4326")
    mock_xr.return_value = fake_da

    da = get_rainfall("NGA", year=2023, month=7)
    assert isinstance(da, xr.DataArray)


@patch("geoafrica.datasets.climate.get_rainfall")
@patch("geoafrica.analysis.zonal_stats.compute")
@patch("geoafrica.datasets.boundaries.get_country")
def test_monthly_series(mock_boundary, mock_compute, mock_rainfall):
    from geoafrica.datasets.climate import monthly_series
    
    fake_da = xr.DataArray(np.zeros((10, 10)))
    mock_rainfall.return_value = fake_da
    mock_compute.return_value = pd.DataFrame({"mean": [123.4], "max": [200]})

    df = monthly_series("Ghana", year=2023)
    assert len(df) == 12
    assert "mean_rainfall_mm" in df.columns


@patch("geoafrica.datasets.climate.get_rainfall")
@patch("geoafrica.datasets.boundaries.get_country")
def test_rainfall_anomaly(mock_boundary, mock_rainfall):
    from geoafrica.datasets.climate import rainfall_anomaly
    
    # Mock get_rainfall to yield a 10x10 array of 100.0 for current year, 80.0 for historical
    def mock_get_rainfall(c, year):
        if year == 2022:
            return xr.DataArray(np.full((10, 10), 100.0), dims=["y", "x"])
        return xr.DataArray(np.full((10, 10), 80.0), dims=["y", "x"])
        
    mock_rainfall.side_effect = mock_get_rainfall

    anomaly = rainfall_anomaly("Senegal", year=2022)
    assert isinstance(anomaly, xr.DataArray)
    # 100 - 80 = 20
    assert float(anomaly.values.mean()) == 20.0
    assert anomaly.attrs["units"] == "mm"
