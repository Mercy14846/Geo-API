"""
GeoAfrica — Health Facilities Module
======================================
Merczcord Technologies Ltd.

Access global health facility data from HealthSites.io and WHO GHO.

Data Sources
------------
- HealthSites.io (https://healthsites.io) — OSM-based, Africa-focused
- WHO GHO (https://www.who.int/data/gho) — Global Health Observatory

Usage
-----
    from geoafrica import health

    # All health facilities in Kenya
    facilities = health.get_facilities("Kenya")

    # Filter by type
    hospitals  = health.get_facilities("Nigeria", facility_type="hospital")
    clinics    = health.get_facilities("Ghana", facility_type="clinic")

    # Nearest facilities to a coordinate
    nearest = health.nearest_to(lat=6.45, lon=3.39, country="Nigeria", n=5)

    # Facility counts by admin area
    counts = health.count_by_admin("Ethiopia", level=1)
"""

from __future__ import annotations

import math

import geopandas as gpd
import pandas as pd

from geoafrica.core.config import get_config
from geoafrica.core.exceptions import DataNotFoundError
from geoafrica.core.session import GeoAfricaSession

_HEALTHSITES_API = "https://healthsites.io/api/v2/facilities/"
_WHO_GHO_API = "https://ghoapi.azureedge.net/api"

FACILITY_TYPES = [
    "hospital", "clinic", "health_centre", "health_post",
    "pharmacy", "laboratory", "dentist", "maternity",
    "dispensary", "health_facility",
]


def get_facilities(
    country: str,
    facility_type: str | None = None,
    source: str = "healthsites",
    page_size: int = 1000,
) -> gpd.GeoDataFrame:
    """
    Return health facilities for a country as a GeoDataFrame.

    Parameters
    ----------
    country : str
        Country name or ISO-2/ISO-3 code.
    facility_type : str, optional
        Filter by type: hospital, clinic, health_centre, pharmacy, etc.
        If None, returns all facility types.
    source : str
        Data source: 'healthsites' (default) or 'osm'.
    page_size : int
        Results per page for paginated APIs. Max 1000.

    Returns
    -------
    GeoDataFrame with columns: name, facility_type, geometry, ...

    Examples
    --------
    >>> hospitals = health.get_facilities("Nigeria", facility_type="hospital")
    >>> print(f"Found {len(hospitals)} hospitals")
    """
    if source == "healthsites":
        return _fetch_healthsites(country, facility_type, page_size)
    elif source == "osm":
        return _fetch_osm_health(country, facility_type)
    else:
        raise ValueError(f"Unknown source '{source}'. Use 'healthsites' or 'osm'.")


def nearest_to(
    lat: float,
    lon: float,
    country: str,
    n: int = 5,
    facility_type: str | None = None,
) -> gpd.GeoDataFrame:
    """
    Find the *n* nearest health facilities to a given coordinate.

    Parameters
    ----------
    lat : float
        Latitude of the query point.
    lon : float
        Longitude of the query point.
    country : str
        Country to search in.
    n : int
        Number of nearest facilities to return.
    facility_type : str, optional
        Facility type filter.

    Returns
    -------
    GeoDataFrame sorted by distance (column 'distance_km' added).
    """
    facilities = get_facilities(country, facility_type=facility_type)
    if facilities.empty:
        raise DataNotFoundError(
            f"No facilities found in '{country}' to compute nearest.",
            query=country,
        )

    query_pt = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy([lon], [lat]),
        crs="EPSG:4326",
    ).to_crs(epsg=3857)

    fac_proj = facilities.to_crs(epsg=3857)
    qx = query_pt.geometry.x.iloc[0]
    qy = query_pt.geometry.y.iloc[0]

    dists = fac_proj.geometry.apply(
        lambda g: math.sqrt((g.centroid.x - qx) ** 2 + (g.centroid.y - qy) ** 2) / 1000
    )

    facilities = facilities.copy()
    facilities["distance_km"] = dists.values
    return facilities.nsmallest(n, "distance_km").reset_index(drop=True)


def count_by_admin(
    country: str,
    level: int = 1,
    facility_type: str | None = None,
) -> pd.DataFrame:
    """
    Count health facilities per administrative unit.

    Parameters
    ----------
    country : str
        Country name or ISO code.
    level : int
        Admin level (1=state, 2=district).
    facility_type : str, optional
        Filter by facility type.

    Returns
    -------
    DataFrame with columns: admin_name, count, area_km2, facilities_per_100k
    """
    from geoafrica.datasets.boundaries import get_admin

    boundaries = get_admin(country, level=level)
    facilities = get_facilities(country, facility_type=facility_type)

    if facilities.empty:
        raise DataNotFoundError(f"No facilities found for '{country}'.")

    # Spatial join
    joined = gpd.sjoin(facilities, boundaries, how="left", predicate="within")

    # Find the name column from boundaries
    name_cols = [c for c in boundaries.columns if "name" in c.lower() and c != "geometry"]
    name_col = name_cols[0] if name_cols else boundaries.columns[0]

    counts = joined.groupby(f"{name_col}_right").size().reset_index(name="facility_count")
    counts = counts.rename(columns={f"{name_col}_right": "admin_name"})

    # Add area
    boundaries_proj = boundaries.to_crs(epsg=6933)
    boundaries["area_km2"] = boundaries_proj.geometry.area / 1e6

    result = counts.merge(
        boundaries[[name_col, "area_km2"]].rename(columns={name_col: "admin_name"}),
        on="admin_name",
        how="left",
    )
    result["facilities_per_1000km2"] = (
        result["facility_count"] / result["area_km2"] * 1000
    ).round(2)
    return result.sort_values("facility_count", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Internal fetch functions
# ---------------------------------------------------------------------------

def _fetch_healthsites(
    country: str,
    facility_type: str | None,
    page_size: int,
) -> gpd.GeoDataFrame:
    """Fetch facilities from HealthSites.io API with pagination."""
    from geoafrica.datasets.boundaries import _COUNTRY_NAME_TO_ISO2, _resolve_iso3

    # Resolve to ISO-2 for HealthSites API
    c = country.strip()
    if len(c) == 3:
        iso2 = next(
            (k for k, v in {**{v: k for k, v in _COUNTRY_NAME_TO_ISO2.items()}}.items()),
            None
        )
    iso3 = _resolve_iso3(country)

    # map ISO3 → ISO2
    from geoafrica.datasets.boundaries import _ISO2_TO_ISO3
    iso2 = next((k for k, v in _ISO2_TO_ISO3.items() if v == iso3), iso3[:2])

    cfg = get_config()
    api_key = cfg.get_api_key("HEALTHSITES")
    headers = {}
    if api_key:
        headers["Authorization"] = f"Token {api_key}"

    params: dict = {
        "format": "json",
        "page_size": min(page_size, 1000),
        "country": iso2,
    }
    if facility_type:
        params["facility_type"] = facility_type

    all_records = []
    url = _HEALTHSITES_API

    with GeoAfricaSession() as s:
        while url:
            try:
                resp = s._session.get(url, params=params, headers=headers, timeout=60)
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                break

            results = data if isinstance(data, list) else data.get("results", [])
            all_records.extend(results)
            # Handle pagination
            if isinstance(data, dict) and data.get("next"):
                url = data["next"]
                params = {}  # next URL already has params
            else:
                break

    if not all_records:
        # Fallback to OSM
        return _fetch_osm_health(country, facility_type)

    return _parse_healthsites_records(all_records)


def _parse_healthsites_records(records: list) -> gpd.GeoDataFrame:
    """Convert HealthSites API records to a GeoDataFrame."""
    from shapely.geometry import Point

    rows = []
    for r in records:
        loc = r.get("location", {})
        if not loc:
            continue
        coords = loc.get("coordinates") or [None, None]
        if None in coords:
            continue
        rows.append({
            "name": r.get("name", ""),
            "facility_type": r.get("facility_type", ""),
            "osm_type": r.get("osm_type", ""),
            "osm_id": r.get("osm_id", ""),
            "country": r.get("country", ""),
            "source": "HealthSites.io",
            "geometry": Point(coords[0], coords[1]),
        })

    if not rows:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")


def _fetch_osm_health(country: str, facility_type: str | None) -> gpd.GeoDataFrame:
    """Fetch health facilities from OSM via Overpass as a fallback."""
    from geoafrica.datasets.osm import get_features

    if facility_type in ("hospital", "clinic"):
        pass

    try:
        gdf = get_features(country, tags={"amenity": ["hospital", "clinic", "health_centre", "pharmacy"]})
        gdf["source"] = "OpenStreetMap"
        return gdf
    except Exception:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
