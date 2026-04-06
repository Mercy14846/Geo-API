"""
Tests for geoafrica.datasets.population
"""
import pytest
from unittest.mock import patch, MagicMock
import numpy as np
import pandas as pd
import xarray as xr


@patch("geoafrica.datasets.population.GeoAfricaSession")
def test_available_years(mock_session):
    from geoafrica.datasets.population import available_years
    
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "success": True,
        "data": [{"ext": "2020"}, {"ext": "2015"}, {"ext": "nonsense"}]
    }
    mock_session.return_value.__enter__.return_value.get.return_value = mock_resp

    years = available_years("NGA")
    assert 2015 in years
    assert 2020 in years


@patch("geoafrica.datasets.population._fetch_worldpop")
def test_get_grid(mock_fetch):
    from geoafrica.datasets.population import get_grid
    
    # Mock data array
    fake_da = xr.DataArray(np.zeros((10, 10)), dims=["y", "x"])
    mock_fetch.return_value = fake_da

    da = get_grid("NGA", year=2020)
    assert isinstance(da, xr.DataArray)
    mock_fetch.assert_called_once()


@patch("geoafrica.datasets.population.get_grid")
@patch("geoafrica.datasets.boundaries.get_admin")
@patch("geoafrica.analysis.zonal_stats.compute")
def test_get_stats(mock_compute, mock_get_admin, mock_get_grid):
    from geoafrica.datasets.population import get_stats
    import geopandas as gpd
    
    mock_get_admin.return_value = gpd.GeoDataFrame(
        {"name": ["Lagos"]}, geometry=[], crs="EPSG:4326"
    )
    mock_get_grid.return_value = xr.DataArray(np.zeros((10, 10)))
    mock_compute.return_value = pd.DataFrame({"zone": ["Lagos"], "sum": [15000000]})

    df = get_stats("Lagos", country="Nigeria", level=1)
    assert not df.empty
    assert "population" in df.columns
