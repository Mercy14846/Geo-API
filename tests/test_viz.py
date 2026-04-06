"""
Tests for geoafrica.viz.maps
"""
import pytest
import geopandas as gpd
from shapely.geometry import Point, box


@pytest.fixture
def fake_points():
    return gpd.GeoDataFrame(
        {"name": ["A", "B"], "value": [10, 20]},
        geometry=[Point(0, 0), Point(1, 1)],
        crs="EPSG:4326"
    )

@pytest.fixture
def fake_polygons():
    return gpd.GeoDataFrame(
        {"name": ["A", "B"], "pop": [100, 200]},
        geometry=[box(0, 0, 1, 1), box(2, 2, 3, 3)],
        crs="EPSG:4326"
    )


def test_quick_map_points(fake_points):
    from geoafrica.viz.maps import quick_map
    import folium
    
    m = quick_map(fake_points)
    assert isinstance(m, folium.Map)


def test_quick_map_polygons(fake_polygons):
    from geoafrica.viz.maps import quick_map
    import folium
    
    m = quick_map(fake_polygons, tooltip_cols=["name"])
    assert isinstance(m, folium.Map)


def test_choropleth(fake_polygons):
    from geoafrica.viz.maps import choropleth
    import folium
    
    m = choropleth(fake_polygons, column="pop", title="Test Map")
    assert isinstance(m, folium.Map)


def test_add_layer(fake_polygons, fake_points):
    from geoafrica.viz.maps import quick_map, add_layer
    import folium
    
    m = quick_map(fake_polygons)
    m2 = add_layer(m, fake_points, name="PointsLayer")
    assert isinstance(m2, folium.Map)
