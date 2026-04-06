"""
Tests for geoafrica.datasets.osm
"""
import pytest
import geopandas as gpd
from unittest.mock import patch, MagicMock


FAKE_OVERPASS_RESPONSE = {
    "elements": [
        {
            "type": "node",
            "id": 1001,
            "lat": 6.4550,
            "lon": 3.3841,
            "tags": {
                "amenity": "hospital",
                "name": "General Hospital Lagos",
            },
        },
        {
            "type": "node",
            "id": 1002,
            "lat": 6.4800,
            "lon": 3.4100,
            "tags": {
                "amenity": "hospital",
                "name": "Island Hospital",
            },
        },
    ]
}

FAKE_BBOX = [3.0, 6.3, 3.9, 6.7]


class TestParseOverpassResponse:
    def test_nodes_to_points(self):
        from geoafrica.datasets.osm import _parse_overpass_response
        gdf = _parse_overpass_response(FAKE_OVERPASS_RESPONSE)
        assert isinstance(gdf, gpd.GeoDataFrame)
        assert len(gdf) == 2
        assert gdf.crs.to_epsg() == 4326
        assert gdf.geometry.geom_type.eq("Point").all()

    def test_empty_response(self):
        from geoafrica.datasets.osm import _parse_overpass_response
        gdf = _parse_overpass_response({"elements": []})
        assert len(gdf) == 0

    def test_tags_preserved(self):
        from geoafrica.datasets.osm import _parse_overpass_response
        gdf = _parse_overpass_response(FAKE_OVERPASS_RESPONSE)
        assert "name" in gdf.columns
        assert "amenity" in gdf.columns
        assert gdf["name"].iloc[0] == "General Hospital Lagos"


class TestBuildOverpassQuery:
    def test_single_tag(self):
        from geoafrica.datasets.osm import _build_overpass_query
        q = _build_overpass_query("4.0,6.0,5.0,7.0", {"amenity": "hospital"}, ["node", "way"], 60)
        assert "amenity" in q
        assert "hospital" in q
        assert "[out:json]" in q

    def test_list_values(self):
        from geoafrica.datasets.osm import _build_overpass_query
        q = _build_overpass_query("4.0,6.0,5.0,7.0", {"amenity": ["hospital", "clinic"]}, ["node"], 60)
        assert "hospital" in q
        assert "clinic" in q


class TestGeocodeTobbox:
    def test_valid_location(self):
        """Test that geocoding returns a 4-element list."""
        fake_nominatim = [
            {
                "lat": "6.455027",
                "lon": "3.384082",
                "boundingbox": ["5.0", "7.0", "2.0", "4.0"],
            }
        ]
        with patch("geoafrica.datasets.osm.GeoAfricaSession") as MockSession:
            mock_resp = MagicMock()
            mock_resp.json.return_value = fake_nominatim
            MockSession.return_value.__enter__.return_value.get.return_value = mock_resp

            from geoafrica.datasets.osm import _geocode_to_bbox
            bbox = _geocode_to_bbox("Lagos Test")
            assert len(bbox) == 4

    def test_not_found_raises(self):
        from geoafrica.datasets.osm import _geocode_to_bbox
        from geoafrica.core.exceptions import DataNotFoundError
        with patch("geoafrica.datasets.osm.GeoAfricaSession") as MockSession:
            mock_resp = MagicMock()
            mock_resp.json.return_value = []
            MockSession.return_value.__enter__.return_value.get.return_value = mock_resp
            with pytest.raises(DataNotFoundError):
                _geocode_to_bbox("NoSuchPlaceXYZ12345")


class TestGetFeaturesbbox:
    def test_returns_geodataframe(self):
        with patch("geoafrica.datasets.osm._run_overpass_query", return_value=FAKE_OVERPASS_RESPONSE):
            from geoafrica.datasets.osm import get_features_bbox
            gdf = get_features_bbox(FAKE_BBOX, tags={"amenity": "hospital"})
            assert isinstance(gdf, gpd.GeoDataFrame)
            assert len(gdf) == 2

    def test_invalid_bbox_raises(self):
        from geoafrica.datasets.osm import get_features_bbox
        from geoafrica.core.exceptions import InvalidBoundingBoxError
        with pytest.raises(InvalidBoundingBoxError):
            get_features_bbox([1, 2], tags={"amenity": "hospital"})
