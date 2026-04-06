"""
Tests for geoafrica.analysis (spatial, zonal_stats, proximity)
"""
import pytest
import numpy as np
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon, box


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def simple_polygons():
    """Two non-overlapping polygons."""
    return gpd.GeoDataFrame(
        {"name": ["ZoneA", "ZoneB"], "area_tag": ["A", "B"]},
        geometry=[
            box(0, 0, 1, 1),
            box(2, 0, 3, 1),
        ],
        crs="EPSG:4326",
    )


@pytest.fixture
def points_inside():
    """Points, one inside ZoneA, one inside ZoneB."""
    return gpd.GeoDataFrame(
        {"facility": ["HospA", "HospB"]},
        geometry=[Point(0.5, 0.5), Point(2.5, 0.5)],
        crs="EPSG:4326",
    )


@pytest.fixture
def points_origin():
    return gpd.GeoDataFrame(
        {"village": ["V1", "V2"]},
        geometry=[Point(0.1, 0.1), Point(2.9, 0.9)],
        crs="EPSG:4326",
    )


# ──────────────────────────────────────────────────────────────────────────────
# spatial module
# ──────────────────────────────────────────────────────────────────────────────
class TestSpatialClip:
    def test_clip_reduces_features(self, simple_polygons, points_inside):
        from geoafrica.analysis.spatial import clip
        mask = simple_polygons.iloc[[0]]  # only ZoneA
        result = clip(points_inside, mask)
        assert len(result) == 1
        assert result["facility"].iloc[0] == "HospA"

    def test_clip_with_geoseries(self, simple_polygons, points_inside):
        from geoafrica.analysis.spatial import clip
        result = clip(points_inside, simple_polygons.geometry)
        assert len(result) == 2


class TestSpatialBuffer:
    def test_buffer_expands_geometry(self, points_inside):
        from geoafrica.analysis.spatial import buffer_km
        buffered = buffer_km(points_inside, km=5)
        assert isinstance(buffered, gpd.GeoDataFrame)
        # Buffered geometry should be larger (area > 0)
        assert all(buffered.geometry.area > 0)

    def test_buffer_preserves_crs(self, simple_polygons):
        from geoafrica.analysis.spatial import buffer_km
        result = buffer_km(simple_polygons, km=1)
        assert result.crs == simple_polygons.crs

    def test_buffer_zero_km(self, points_inside):
        from geoafrica.analysis.spatial import buffer_km
        result = buffer_km(points_inside, km=0)
        assert len(result) == len(points_inside)


class TestSpatialDissolve:
    def test_dissolve_reduces_rows(self, simple_polygons):
        from geoafrica.analysis.spatial import dissolve_by
        # Add a shared column to dissolve on
        gdf = simple_polygons.copy()
        gdf["region"] = ["West", "West"]
        result = dissolve_by(gdf, column="region")
        assert len(result) == 1

    def test_dissolve_preserves_geometry_type(self, simple_polygons):
        from geoafrica.analysis.spatial import dissolve_by
        gdf = simple_polygons.copy()
        gdf["group"] = ["G1", "G2"]
        result = dissolve_by(gdf, column="group")
        assert len(result) == 2


class TestWithinDistance:
    def test_filters_correctly(self, points_inside):
        from geoafrica.analysis.spatial import within_distance
        # ZoneA hospital is near (0.5, 0.5), ZoneB is far
        result = within_distance(points_inside, point_lon=0.5, point_lat=0.5, km=500)
        assert len(result) >= 1
        assert "distance_km" in result.columns

    def test_distance_column_sorted(self, points_inside):
        from geoafrica.analysis.spatial import within_distance
        result = within_distance(points_inside, point_lon=0.5, point_lat=0.5, km=999)
        if len(result) > 1:
            assert result["distance_km"].iloc[0] <= result["distance_km"].iloc[1]


class TestBboxToPolygon:
    def test_returns_geodataframe(self):
        from geoafrica.analysis.spatial import bbox_to_polygon
        gdf = bbox_to_polygon([3.0, 6.0, 5.0, 8.0])
        assert isinstance(gdf, gpd.GeoDataFrame)
        assert len(gdf) == 1
        assert gdf.geometry.geom_type.iloc[0] == "Polygon"


# ──────────────────────────────────────────────────────────────────────────────
# proximity module
# ──────────────────────────────────────────────────────────────────────────────
class TestNearestFacility:
    def test_returns_nearest(self, points_origin, points_inside):
        from geoafrica.analysis.proximity import nearest_facility
        result = nearest_facility(points_origin, points_inside, n=1)
        assert isinstance(result, gpd.GeoDataFrame)
        assert "nearest_name" in result.columns
        assert "nearest_distance_km" in result.columns
        assert len(result) == len(points_origin)

    def test_distance_non_negative(self, points_origin, points_inside):
        from geoafrica.analysis.proximity import nearest_facility
        result = nearest_facility(points_origin, points_inside, n=1)
        assert all(result["nearest_distance_km"] >= 0)


class TestPointInPolygon:
    def test_join_assigns_polygon_attrs(self, points_inside, simple_polygons):
        from geoafrica.analysis.proximity import point_in_polygon
        result = point_in_polygon(points_inside, simple_polygons)
        assert "name" in result.columns or "name_right" in result.columns


# ──────────────────────────────────────────────────────────────────────────────
# zonal_stats module
# ──────────────────────────────────────────────────────────────────────────────
class TestZonalStats:
    def test_invalid_stat_raises(self, simple_polygons):
        from geoafrica.analysis.zonal_stats import compute
        import xarray as xr

        fake_raster = xr.DataArray(
            np.ones((1, 100, 100)),
            dims=["band", "y", "x"],
        )
        with pytest.raises(ValueError, match="Unknown stat"):
            compute(fake_raster, simple_polygons, stats=["invalid_stat"])
