"""
Tests for geoafrica.datasets.boundaries
"""
import pytest
import pandas as pd


# ---------------------------------------------------------------------------
# _resolve_iso3
# ---------------------------------------------------------------------------
class TestResolveISO3:
    def test_full_name(self):
        from geoafrica.datasets.boundaries import _resolve_iso3
        assert _resolve_iso3("Nigeria") == "NGA"
        assert _resolve_iso3("nigeria") == "NGA"
        assert _resolve_iso3("Ghana")   == "GHA"
        assert _resolve_iso3("Kenya")   == "KEN"

    def test_iso2(self):
        from geoafrica.datasets.boundaries import _resolve_iso3
        assert _resolve_iso3("NG") == "NGA"
        assert _resolve_iso3("GH") == "GHA"
        assert _resolve_iso3("ZA") == "ZAF"

    def test_iso3_passthrough(self):
        from geoafrica.datasets.boundaries import _resolve_iso3
        assert _resolve_iso3("NGA") == "NGA"
        assert _resolve_iso3("ETH") == "ETH"

    def test_unknown_raises(self):
        from geoafrica.datasets.boundaries import _resolve_iso3
        from geoafrica.core.exceptions import DataNotFoundError
        with pytest.raises(DataNotFoundError):
            _resolve_iso3("XYZ_UNKNOWN_COUNTRY_123")


# ---------------------------------------------------------------------------
# list_countries
# ---------------------------------------------------------------------------
class TestListCountries:
    def test_returns_dataframe(self):
        from geoafrica.datasets.boundaries import list_countries
        df = list_countries()
        assert isinstance(df, pd.DataFrame)
        assert "country" in df.columns
        assert "iso2" in df.columns
        assert "iso3" in df.columns

    def test_africa_filter(self):
        from geoafrica.datasets.boundaries import list_countries
        df = list_countries(region="Africa")
        assert len(df) > 40
        assert all(df["region"] == "Africa")

    def test_no_duplicate_iso2(self):
        from geoafrica.datasets.boundaries import list_countries
        df = list_countries()
        assert df["iso2"].duplicated().sum() == 0


# ---------------------------------------------------------------------------
# get_bbox
# ---------------------------------------------------------------------------
class TestGetBBox:
    def test_returns_four_floats(self):
        """Mock GADM response to avoid real HTTP calls."""
        import geopandas as gpd
        from shapely.geometry import box
        from unittest.mock import patch

        fake_gdf = gpd.GeoDataFrame(
            geometry=[box(2.5, 4.0, 14.8, 13.9)],
            crs="EPSG:4326"
        )
        with patch("geoafrica.datasets.boundaries._fetch_gadm", return_value=fake_gdf):
            from geoafrica.datasets.boundaries import get_bbox
            bbox = get_bbox("Nigeria")
            assert len(bbox) == 4
            assert bbox[0] < bbox[2]  # min_lon < max_lon
            assert bbox[1] < bbox[3]  # min_lat < max_lat
