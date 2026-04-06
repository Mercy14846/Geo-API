"""
Tests for geoafrica.datasets.fire
"""
import pytest
from unittest.mock import patch, MagicMock
import geopandas as gpd
import pandas as pd


SAMPLE_FIRMS_CSV = """latitude,longitude,bright_ti4,acq_date,acq_time,satellite,confidence,frp
6.2345,3.1234,320.5,2024-01-15,0145,N,high,15.2
6.8901,4.5678,335.1,2024-01-15,0145,N,nominal,8.7
7.1234,3.9012,310.8,2024-01-15,0150,N,low,5.1
"""


class TestParseFirmsCSV:
    def test_valid_csv(self):
        from geoafrica.datasets.fire import _parse_firms_csv
        gdf = _parse_firms_csv(SAMPLE_FIRMS_CSV)
        assert isinstance(gdf, gpd.GeoDataFrame)
        assert len(gdf) == 3
        assert gdf.crs.to_epsg() == 4326
        assert gdf.geometry.geom_type.eq("Point").all()

    def test_empty_response(self):
        from geoafrica.datasets.fire import _parse_firms_csv
        gdf = _parse_firms_csv("")
        assert isinstance(gdf, gpd.GeoDataFrame)
        assert len(gdf) == 0

    def test_error_response(self):
        from geoafrica.datasets.fire import _parse_firms_csv
        gdf = _parse_firms_csv("Sorry, your request could not be processed.")
        assert len(gdf) == 0

    def test_columns_preserved(self):
        from geoafrica.datasets.fire import _parse_firms_csv
        gdf = _parse_firms_csv(SAMPLE_FIRMS_CSV)
        assert "latitude" in gdf.columns
        assert "longitude" in gdf.columns
        assert "acq_date" in gdf.columns
        assert "frp" in gdf.columns

    def test_coordinate_values(self):
        from geoafrica.datasets.fire import _parse_firms_csv
        gdf = _parse_firms_csv(SAMPLE_FIRMS_CSV)
        assert abs(float(gdf.geometry.x.iloc[0]) - 3.1234) < 0.001
        assert abs(float(gdf.geometry.y.iloc[0]) - 6.2345) < 0.001


class TestFireSummary:
    def test_summary_by_date(self):
        from geoafrica.datasets.fire import _parse_firms_csv, summary
        gdf = _parse_firms_csv(SAMPLE_FIRMS_CSV)
        s = summary(gdf, by="acq_date")
        assert isinstance(s, pd.DataFrame)
        assert "count" in s.columns

    def test_empty_summary(self):
        from geoafrica.datasets.fire import summary
        gdf = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
        result = summary(gdf)
        assert result.empty


class TestGetFirmsKey:
    def test_missing_key_raises(self):
        from geoafrica.datasets.fire import _get_firms_key
        from geoafrica.core.exceptions import APIKeyMissingError
        import os
        key = os.environ.pop("GEOAFRICA_FIRMS_KEY", None)
        try:
            with pytest.raises(APIKeyMissingError):
                _get_firms_key()
        finally:
            if key:
                os.environ["GEOAFRICA_FIRMS_KEY"] = key

    def test_key_from_env(self, monkeypatch):
        from geoafrica.datasets.fire import _get_firms_key
        from geoafrica.core.config import _default_config
        import geoafrica.core.config as cfg_mod
        monkeypatch.setenv("GEOAFRICA_FIRMS_KEY", "test_key_123")
        cfg_mod._default_config = None  # force re-init
        key = _get_firms_key()
        assert key == "test_key_123"
