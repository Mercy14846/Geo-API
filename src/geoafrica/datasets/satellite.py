"""
GeoAfrica — Satellite Imagery Module
=======================================
Merczcord Technologies Ltd.

Search and access satellite imagery from Digital Earth Africa,
Sentinel-2, and Landsat via STAC catalogs.

Data Sources
------------
- Digital Earth Africa STAC (https://explorer.digitalearth.africa)
- Element 84 Earth Search (https://earth-search.aws.element84.com)
- Microsoft Planetary Computer (https://planetarycomputer.microsoft.com)

Usage
-----
    from geoafrica import satellite

    # Search for Sentinel-2 scenes over Kenya
    items = satellite.search(
        collection="sentinel-2-l2a",
        bbox=[33.9, -1.4, 41.9, 4.6],
        date_range="2023-01-01/2023-12-31",
        max_cloud_cover=20,
        limit=10,
    )

    # Load an RGB composite
    ds = satellite.load_rgb(items[0])

    # Available collections for Africa
    cols = satellite.list_collections()
"""

from __future__ import annotations

import pandas as pd

from geoafrica.core.exceptions import DataNotFoundError

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pystac
    import xarray

# STAC catalog endpoints
STAC_CATALOGS = {
    "deafrica": "https://explorer.digitalearth.africa/stac",
    "earth_search": "https://earth-search.aws.element84.com/v1",
    "planetary_computer": "https://planetarycomputer.microsoft.com/api/stac/v1",
}

# Well-known collections available per catalog
COLLECTIONS = {
    "sentinel-2-l2a": "earth_search",
    "landsat-c2-l2": "earth_search",
    "sentinel-1-rtc": "earth_search",
    "cop-dem-glo-30": "earth_search",
    "ga_ls8c_ard_3": "deafrica",
    "s2_l2a": "deafrica",
    "ga_s2_gm_annual_3": "deafrica",
    "rainfall_chirps_monthly": "deafrica",
    "ls8_sr": "deafrica",
    "wofs_ls": "deafrica",
}


def search(
    collection: str,
    bbox: list[float] | None = None,
    country: str | None = None,
    location: str | None = None,
    date_range: str = "2023-01-01/2023-12-31",
    max_cloud_cover: int = 20,
    limit: int = 10,
    catalog: str | None = None,
) -> "pystac.ItemCollection":
    """
    Search STAC catalogs for satellite imagery.

    Parameters
    ----------
    collection : str
        STAC collection ID (e.g. 'sentinel-2-l2a', 's2_l2a').
    bbox : list of float, optional
        [min_lon, min_lat, max_lon, max_lat]. Provide this OR country OR location.
    country : str, optional
        Country name/ISO code (auto-computes bbox). Provide this OR bbox OR location.
    location: str, optional
        Specific city, state, or region (auto-computes bbox via geocoding).
    date_range : str
        ISO-8601 date range 'YYYY-MM-DD/YYYY-MM-DD'.
    max_cloud_cover : int
        Maximum cloud cover percentage (0–100).
    limit : int
        Maximum number of items to return.
    catalog : str, optional
        STAC catalog: 'deafrica', 'earth_search', 'planetary_computer'.
        Auto-selected if not provided.

    Returns
    -------
    pystac.ItemCollection

    Examples
    --------
    >>> items = satellite.search(
    ...     collection="sentinel-2-l2a",
    ...     country="Rwanda",
    ...     date_range="2023-06-01/2023-09-30",
    ...     max_cloud_cover=15,
    ... )
    >>> print(f"Found {len(items)} scenes")
    """
    try:
        import pystac_client
    except ImportError:
        raise ImportError(
            "Install satellite dependencies: pip install \"geoafrica[satellite]\""
        )

    if country and bbox is None:
        from geoafrica.datasets.boundaries import get_bbox
        bbox = get_bbox(country)

    if location and bbox is None:
        import geopandas as gpd
        # Geocode the location directly using Nominatim (requires network)
        gdf = gpd.tools.geocode(location, provider="nominatim", user_agent="geoafrica_sdk")
        if gdf.empty or gdf["geometry"].iloc[0] is None:
            raise ValueError(f"Could not find coordinates for location: '{location}'")
        bounds = gdf.total_bounds # [minx, miny, maxx, maxy]

        # If it's a single point rather than a region, buffer it slightly 
        # so STAC catches intersecting images
        if bounds[0] == bounds[2] and bounds[1] == bounds[3]:
            # ~10km buffer roughly (0.1 degrees)
            bbox = [bounds[0]-0.1, bounds[1]-0.1, bounds[2]+0.1, bounds[3]+0.1]
        else:
            bbox = list(bounds)

    if bbox is None:
        raise ValueError("Provide either 'bbox', 'country', or 'location'.")

    # Auto-select catalog
    if catalog is None:
        catalog = COLLECTIONS.get(collection, "earth_search")

    endpoint = STAC_CATALOGS.get(catalog, catalog)

    client = pystac_client.Client.open(endpoint)

    search_params = {
        "collections": [collection],
        "bbox": bbox,
        "datetime": date_range,
        "max_items": limit,
        "query": {"eo:cloud_cover": {"lte": max_cloud_cover}},
    }

    results = client.search(**search_params)
    items = results.item_collection()

    if len(items) == 0:
        raise DataNotFoundError(
            f"No items found for collection '{collection}' with the given parameters.",
            query=collection,
        )

    return items


def load_rgb(
    item: "pystac.Item",
    resolution: int = 10,
) -> "xarray.Dataset":
    """
    Load an RGB (true colour) composite from a STAC item.

    Parameters
    ----------
    item : pystac.Item
        A single STAC item (e.g. from search()).
    resolution : int
        Target resolution in metres. Default 10.

    Returns
    -------
    xarray.Dataset with 'red', 'green', 'blue' data variables.
    """
    try:
        import stackstac
    except ImportError:
        raise ImportError("Install stackstac: pip install geoafrica[satellite]")

    # Identify RGB band names (varies by collection)
    assets = list(item.assets.keys())
    band_map = {
        "red": next((a for a in assets if a in ("red", "B04", "B4", "band4")), None),
        "green": next((a for a in assets if a in ("green", "B03", "B3", "band3")), None),
        "blue": next((a for a in assets if a in ("blue", "B02", "B2", "band2")), None),
    }
    bands = [v for v in band_map.values() if v]

    ds = stackstac.stack(
        [item],
        assets=bands,
        resolution=resolution,
        epsg=4326,
    )
    return ds


def list_collections(catalog: str = "earth_search") -> pd.DataFrame:
    """
    List available STAC collections from a catalog.

    Parameters
    ----------
    catalog : str
        'deafrica', 'earth_search', or 'planetary_computer'.

    Returns
    -------
    DataFrame with: id, title, description, extent
    """
    try:
        import pystac_client
    except ImportError:
        raise ImportError("Install: pip install geoafrica[satellite]")

    endpoint = STAC_CATALOGS.get(catalog, catalog)
    client = pystac_client.Client.open(endpoint)

    collections = list(client.get_collections())
    records = []
    for col in collections:
        records.append({
            "id": col.id,
            "title": col.title or "",
            "description": (col.description or "")[:120],
            "catalog": catalog,
        })
    return pd.DataFrame(records).sort_values("id").reset_index(drop=True)


def deafrica_products() -> pd.DataFrame:
    """
    List all Digital Earth Africa products (Africa-specific collections).

    Returns
    -------
    DataFrame with product names and descriptions.
    """
    return list_collections(catalog="deafrica")
