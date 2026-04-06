"""
Tests for geoafrica.datasets.climate
"""
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import xarray as xr
import numpy as np


@patch("geoafrica.datasets.climate.GeoAfricaSession")
@patch("geoafrica.datasets.climate.xr.open_dataarray")
def test_get_rainfall(mock_xr, mock_session):
    from geoafrica.datasets.climate import get_rainfall
    
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
@patch("geoafrica.analysis.zonal_stats.compute")
@patch("geoafrica.datasets.boundaries.get_country")
def test_rainfall_anomaly(mock_boundary, mock_compute, mock_rainfall):
    from geoafrica.datasets.climate import rainfall_anomaly
    
    fake_da = xr.DataArray(np.zeros((10, 10)))
    mock_rainfall.return_value = fake_da
    # Mock compute returns 100 for current year, 80 for historical
    mock_compute.side_effect = [
        pd.DataFrame({"mean": [100.0]}),  # Active year
        *[pd.DataFrame({"mean": [80.0]})] * 30  # Historical years
    ]

    anomaly = rainfall_anomaly("Senegal", year=2022)
    assert anomaly["annual_mm"] == 100.0
    assert anomaly["anomaly_pct"] == 25.0
