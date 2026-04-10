"""
GeoAfrica — OpenStreetMap Module
==================================
Merczcord Technologies Ltd.

Query any OpenStreetMap features for any location in the world via the
Overpass API — no API key required.

Usage
-----
    from geoafrica import osm

    # Hospitals in Lagos
    hospitals = osm.get_features("Lagos, Nigeria", tags={"amenity": "hospital"})

    # All primary roads in Nairobi
    roads = osm.get_roads("Nairobi", road_type="primary")

    # Schools in Ghana
    schools = osm.get_features("Ghana", tags={"amenity": "school"})

    # Water bodies in Ethiopia
    water = osm.get_features("Ethiopia", tags={"natural": "water"})

    # Search with a bounding box
    markets = osm.get_features_bbox(
        bbox=[3.0, 6.3, 3.5, 6.7],
        tags={"amenity": "marketplace"}
    )
"""

from __future__ import annotations

import json

import geopandas as gpd
from shapely.geometry import LineString, Point, Polygon

from geoafrica.core.config import get_config
from geoafrica.core.exceptions import DataNotFoundError, InvalidBoundingBoxError
from geoafrica.core.session import GeoAfricaSession

# Overpass API endpoints (public mirrors)
_OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
]

# Common tag presets for convenience
AMENITY_PRESETS = {
    "hospital": {"amenity": "hospital"},
    "clinic": {"amenity": "clinic"},
    "school": {"amenity": "school"},
    "university": {"amenity": "university"},
    "pharmacy": {"amenity": "pharmacy"},
    "bank": {"amenity": "bank"},
    "market": {"amenity": "marketplace"},
    "police": {"amenity": "police"},
    "fire_station": {"amenity": "fire_station"},
    "water": {"amenity": "drinking_water"},
    "place_of_worship": {"amenity": "place_of_worship"},
    "restaurant": {"amenity": "restaurant"},
    "fuel": {"amenity": "fuel"},
    "atm": {"amenity": "atm"},
}

ROAD_TYPES = [
    "motorway",
    "trunk",
    "primary",
    "secondary",
    "tertiary",
    "residential",
    "track",
    "path",
]


def get_features(
    location: str,
    tags: dict[str, str | list[str]],
    geometry_types: list[str] = ("node", "way", "relation"),
    timeout: int = 120,
) -> gpd.GeoDataFrame:
    """
    Fetch OSM features matching *tags* within a named location.

    Parameters
    ----------
    location : str
        Location name resolvable via Nominatim (e.g. "Lagos, Nigeria",
        "Nairobi", "Ethiopia").
    tags : dict
        OSM tags to filter by. Values can be a string or list of strings.
        e.g. {"amenity": "hospital"} or {"amenity": ["hospital", "clinic"]}
    geometry_types : list of str
        OSM element types to query: 'node', 'way', 'relation'. Default: all.
    timeout : int
        Overpass query timeout in seconds. Defaults to 120.

    Returns
    -------
    GeoDataFrame (CRS=EPSG:4326)

    Examples
    --------
    >>> hospitals = osm.get_features("Kenya", tags={"amenity": "hospital"})
    >>> len(hospitals)
    847
    """
    bbox = _geocode_to_bbox(location)
    return get_features_bbox(bbox=bbox, tags=tags, geometry_types=geometry_types, timeout=timeout)


def get_features_bbox(
    bbox: list[float],
    tags: dict[str, str | list[str]],
    geometry_types: list[str] = ("node", "way", "relation"),
    timeout: int = 120,
) -> gpd.GeoDataFrame:
    """
    Fetch OSM features matching *tags* within a bounding box.

    Parameters
    ----------
    bbox : list of float
        [min_lon, min_lat, max_lon, max_lat]
    tags : dict
        OSM tags to filter.
    geometry_types : list of str
        OSM element types: 'node', 'way', 'relation'.
    timeout : int
        Overpass query timeout.

    Returns
    -------
    GeoDataFrame
    """
    if len(bbox) != 4:
        raise InvalidBoundingBoxError(bbox)

    min_lon, min_lat, max_lon, max_lat = bbox
    overpass_bbox = f"{min_lat},{min_lon},{max_lat},{max_lon}"

    query = _build_overpass_query(overpass_bbox, tags, geometry_types, timeout)
    data = _run_overpass_query(query)
    return _parse_overpass_response(data)


def get_roads(
    location: str,
    road_type: str | None = None,
    timeout: int = 120,
) -> gpd.GeoDataFrame:
    """
    Fetch road network from OSM for a location.

    Parameters
    ----------
    location : str
        Location name (geocoded via Nominatim).
    road_type : str, optional
        OSM highway type filter: 'primary', 'secondary', 'residential', etc.
        If None, returns all road types.
    timeout : int
        Overpass query timeout.

    Returns
    -------
    GeoDataFrame with road geometries (LineStrings)

    Examples
    --------
    >>> roads = osm.get_roads("Abuja, Nigeria", road_type="primary")
    """
    tags: dict[str, str | list[str]] = {}
    if road_type:
        if road_type not in ROAD_TYPES:
            raise ValueError(f"road_type must be one of: {ROAD_TYPES}")
        tags = {"highway": road_type}
    else:
        tags = {"highway": ROAD_TYPES}

    return get_features(location, tags=tags, geometry_types=["way"], timeout=timeout)


def get_amenity(
    location: str,
    amenity: str,
    timeout: int = 120,
) -> gpd.GeoDataFrame:
    """
    Convenience wrapper to fetch a common amenity type.

    Parameters
    ----------
    location : str
        Location name.
    amenity : str
        One of: hospital, clinic, school, university, pharmacy, bank,
        market, police, fire_station, water, place_of_worship, restaurant,
        fuel, atm.

    Returns
    -------
    GeoDataFrame

    Examples
    --------
    >>> schools = osm.get_amenity("Ghana", amenity="school")
    """
    if amenity not in AMENITY_PRESETS:
        raise ValueError(f"Unknown amenity '{amenity}'. Available presets: {list(AMENITY_PRESETS)}")
    tags = AMENITY_PRESETS[amenity]
    return get_features(location, tags=tags, timeout=timeout)


def get_buildings(
    location: str,
    building_type: str | None = None,
    timeout: int = 180,
) -> gpd.GeoDataFrame:
    """
    Fetch building footprints from OSM.

    Parameters
    ----------
    location : str
        Location name.
    building_type : str, optional
        OSM building type (e.g. 'residential', 'commercial', 'yes').

    Returns
    -------
    GeoDataFrame with Polygon geometries.
    """
    tags: dict[str, str | list[str]] = {"building": building_type or "yes"}
    return get_features(location, tags=tags, geometry_types=["way", "relation"], timeout=timeout)


# ---------------------------------------------------------------------------
# Overpass query builder
# ---------------------------------------------------------------------------


def _build_overpass_query(
    bbox: str,
    tags: dict[str, str | list[str]],
    geometry_types: list[str],
    timeout: int,
) -> str:
    """Build an Overpass QL query string."""
    union_blocks = []

    for geom_type in geometry_types:
        tag_filters = ""
        for key, value in tags.items():
            if isinstance(value, list):
                values_str = "|".join(value)
                tag_filters += f'["{key}"~"^({values_str})$"]'
            else:
                tag_filters += f'["{key}"="{value}"]'
        union_blocks.append(f"{geom_type}{tag_filters}({bbox});")

    union = "\n  ".join(union_blocks)
    return f"[out:json][timeout:{timeout}];\n(\n  {union}\n);\nout body;\n>;\nout skel qt;"


def _run_overpass_query(query: str) -> dict:
    """Execute an Overpass QL query, trying multiple endpoints."""
    last_err: Exception | None = None
    for endpoint in _OVERPASS_ENDPOINTS:
        try:
            with GeoAfricaSession() as s:
                resp = s.post(endpoint, data={"data": query})
                return resp.json()
        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"All Overpass API endpoints failed. Last error: {last_err}")


def _parse_overpass_response(data: dict) -> gpd.GeoDataFrame:
    """Parse Overpass JSON response into a GeoDataFrame."""
    elements = data.get("elements", [])
    if not elements:
        return gpd.GeoDataFrame(
            columns=["geometry", "osm_id", "osm_type"],
            geometry="geometry",
            crs="EPSG:4326",
        )

    # Build a node ID → (lat, lon) lookup
    node_map: dict[int, tuple[float, float]] = {}
    for el in elements:
        if el["type"] == "node" and "lat" in el:
            node_map[el["id"]] = (el["lon"], el["lat"])

    records = []
    for el in elements:
        geom = None
        props = {"osm_id": el.get("id"), "osm_type": el.get("type")}
        props.update(el.get("tags", {}))

        if el["type"] == "node" and "lat" in el:
            geom = Point(el["lon"], el["lat"])

        elif el["type"] == "way":
            coords = [node_map[nid] for nid in el.get("nodes", []) if nid in node_map]
            if len(coords) >= 2:
                if coords[0] == coords[-1] and len(coords) >= 4:
                    try:
                        geom = Polygon(coords)
                    except Exception:
                        geom = LineString(coords)
                else:
                    geom = LineString(coords)

        # relations / multipolygons: simplified — use centroid of member nodes
        elif el["type"] == "relation":
            member_coords = []
            for m in el.get("members", []):
                if m.get("type") == "node" and m.get("ref") in node_map:
                    member_coords.append(node_map[m["ref"]])
            if member_coords:
                xs = [c[0] for c in member_coords]
                ys = [c[1] for c in member_coords]
                geom = Point(sum(xs) / len(xs), sum(ys) / len(ys))

        if geom is not None:
            records.append({**props, "geometry": geom})

    if not records:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    gdf = gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:4326")
    # Add human-readable name column if available
    if "name" in gdf.columns:
        gdf["name"] = gdf["name"].fillna("")
    return gdf


def _geocode_to_bbox(location: str) -> list[float]:
    """Geocode a location string to a [min_lon, min_lat, max_lon, max_lat] bbox."""
    cfg = get_config()
    cache_file = cfg.cache_dir / "geocode_cache.json"
    cache: dict[str, list[float]] = {}

    if cache_file.exists():
        try:
            cache = json.loads(cache_file.read_text())
        except Exception:
            pass

    if location in cache:
        return cache[location]

    with GeoAfricaSession(use_cache=False) as s:
        resp = s.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": location,
                "format": "json",
                "limit": 1,
                "polygon_geojson": 0,
            },
        )
        results = resp.json()

    if not results:
        raise DataNotFoundError(
            f"Could not geocode '{location}'. Try a more specific location name.",
            query=location,
        )

    r = results[0]
    bbox_raw = r.get("boundingbox", [])
    if bbox_raw:
        min_lat, max_lat, min_lon, max_lon = map(float, bbox_raw)
    else:
        lon, lat = float(r["lon"]), float(r["lat"])
        delta = 0.2
        min_lat, max_lat = lat - delta, lat + delta
        min_lon, max_lon = lon - delta, lon + delta

    bbox = [min_lon, min_lat, max_lon, max_lat]
    cache[location] = bbox

    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(cache, indent=2))
    except Exception:
        pass

    return bbox
