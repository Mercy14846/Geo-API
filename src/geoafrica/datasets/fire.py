"""
GeoAfrica — NASA FIRMS Fire Module
=====================================
Merczcord Technologies Ltd.

Near real-time and historical active fire detections from NASA FIRMS
using VIIRS and MODIS sensors.

API Key Required
----------------
Register for a free MAP_KEY at: https://firms.modaps.eosdis.nasa.gov/api/
Then configure: geoafrica config set NASA_FIRMS <your_key>
Or: export GEOAFRICA_FIRMS_KEY=<your_key>

Usage
-----
    from geoafrica import fire

    # Active fires in West Africa (last 7 days)
    fires = fire.get_active(bbox=[-18, 4, 30, 20], days=7)

    # Active fires for a country
    nigeria_fires = fire.get_country("Nigeria", days=24)

    # Historical fire data
    hist = fire.get_historical("Kenya", start="2023-06-01", end="2023-08-31")

    # Burn scar (NRT VIIRS)
    burn = fire.get_burn_scar("Ethiopia", year=2023)
"""

from __future__ import annotations

from datetime import datetime, timedelta, date
from typing import Optional, Union

import geopandas as gpd
import pandas as pd

from geoafrica.core.session import GeoAfricaSession
from geoafrica.core.config import get_config
from geoafrica.core.exceptions import APIKeyMissingError, DataNotFoundError, InvalidBoundingBoxError

_FIRMS_BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
_FIRMS_COUNTRY_BASE = "https://firms.modaps.eosdis.nasa.gov/api/country/csv"

# Sensor/product options
SENSORS = {
    "VIIRS_SNPP": "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20": "VIIRS_NOAA20_NRT",
    "MODIS": "MODIS_NRT",
    "VIIRS_SNPP_SP": "VIIRS_SNPP_SP",   # Standard processing (archive)
}

DEFAULT_SENSOR = "VIIRS_SNPP"


def get_active(
    bbox: list[float],
    days: int = 7,
    sensor: str = DEFAULT_SENSOR,
) -> gpd.GeoDataFrame:
    """
    Fetch near real-time active fire detections within a bounding box.

    Parameters
    ----------
    bbox : list of float
        [min_lon, min_lat, max_lon, max_lat]
    days : int
        Number of past days to query (1–10 for NRT data). Default 7.
    sensor : str
        Sensor/product: 'VIIRS_SNPP' (default), 'VIIRS_NOAA20', 'MODIS'.

    Returns
    -------
    GeoDataFrame with fire point locations and confidence, brightness, etc.

    Examples
    --------
    >>> fires = fire.get_active(bbox=[-18, 4, 30, 20], days=7)
    >>> print(f"Detected {len(fires)} fire points")
    """
    if len(bbox) != 4:
        raise InvalidBoundingBoxError(bbox)

    if days < 1 or days > 10:
        raise ValueError("days must be between 1 and 10 for NRT data.")

    api_key = _get_firms_key()
    product = SENSORS.get(sensor.upper(), sensor)
    min_lon, min_lat, max_lon, max_lat = bbox
    bbox_str = f"{min_lon},{min_lat},{max_lon},{max_lat}"

    url = f"{_FIRMS_BASE}/{api_key}/{product}/{bbox_str}/{days}"

    with GeoAfricaSession(use_cache=False) as s:
        resp = s._session.get(url, timeout=60)
        if resp.status_code == 400:
            raise ValueError(f"FIRMS API error: {resp.text}")
        resp.raise_for_status()
        content = resp.text

    return _parse_firms_csv(content, sensor=sensor)


def get_country(
    country: str,
    days: int = 7,
    sensor: str = DEFAULT_SENSOR,
) -> gpd.GeoDataFrame:
    """
    Fetch active fire detections for an entire country.

    Parameters
    ----------
    country : str
        Country name or ISO code.
    days : int
        Past days (1–10).
    sensor : str
        Sensor type.

    Returns
    -------
    GeoDataFrame

    Examples
    --------
    >>> ng_fires = fire.get_country("Nigeria", days=3)
    """
    from geoafrica.datasets.boundaries import _resolve_iso3
    iso3 = _resolve_iso3(country)
    api_key = _get_firms_key()
    product = SENSORS.get(sensor.upper(), sensor)

    url = f"{_FIRMS_COUNTRY_BASE}/{api_key}/{product}/{iso3}/{days}"

    with GeoAfricaSession(use_cache=False) as s:
        resp = s._session.get(url, timeout=60)
        resp.raise_for_status()

    return _parse_firms_csv(resp.text, sensor=sensor)


def get_historical(
    country: str,
    start: Union[str, date],
    end: Union[str, date],
    sensor: str = "VIIRS_SNPP_SP",
) -> gpd.GeoDataFrame:
    """
    Fetch historical fire data for a country and date range.

    Parameters
    ----------
    country : str
        Country or ISO code.
    start, end : str or date
        Date range, e.g. '2023-01-01' to '2023-12-31'.
        Maximum range: 1 year.
    sensor : str
        Use 'VIIRS_SNPP_SP' for archive (standard processing).

    Returns
    -------
    GeoDataFrame
    """
    if isinstance(start, str):
        start = datetime.strptime(start, "%Y-%m-%d").date()
    if isinstance(end, str):
        end = datetime.strptime(end, "%Y-%m-%d").date()

    if (end - start).days > 366:
        raise ValueError("Date range cannot exceed 1 year for historical queries.")

    from geoafrica.datasets.boundaries import _resolve_iso3, get_bbox
    iso3 = _resolve_iso3(country)
    bbox = get_bbox(country)
    api_key = _get_firms_key()
    product = SENSORS.get(sensor.upper(), sensor)

    min_lon, min_lat, max_lon, max_lat = bbox
    bbox_str = f"{min_lon:.4f},{min_lat:.4f},{max_lon:.4f},{max_lat:.4f}"
    date_range = f"{start}/{end}"

    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{api_key}/{product}/{bbox_str}/{date_range}"

    cfg = get_config()
    cache_key = f"firms_{iso3}_{start}_{end}_{sensor}.csv"
    cache_path = cfg.cache_dir / "fire" / cache_key

    if cache_path.exists():
        df = pd.read_csv(cache_path)
        return _df_to_geodataframe(df)

    with GeoAfricaSession(use_cache=False) as s:
        resp = s._session.get(url, timeout=120)
        resp.raise_for_status()

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(resp.text)

    return _parse_firms_csv(resp.text, sensor=sensor)


def summary(gdf: gpd.GeoDataFrame, by: str = "confidence") -> pd.DataFrame:
    """
    Summarize fire detections.

    Parameters
    ----------
    gdf : GeoDataFrame
        Output from get_active / get_country / get_historical.
    by : str
        Group by column: 'confidence', 'acq_date', etc.

    Returns
    -------
    DataFrame with counts and brightness stats.
    """
    if gdf.empty:
        return pd.DataFrame()
    if by not in gdf.columns:
        by = "acq_date" if "acq_date" in gdf.columns else gdf.columns[0]
    return (
        gdf.groupby(by)
        .agg(
            count=("geometry", "count"),
            avg_brightness=("bright_ti4", "mean") if "bright_ti4" in gdf.columns else ("geometry", "count"),
            frp_sum=("frp", "sum") if "frp" in gdf.columns else ("geometry", "count"),
        )
        .reset_index()
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_firms_key() -> str:
    """Return the NASA FIRMS API key or raise a clear error."""
    cfg = get_config()
    key = cfg.get_api_key("NASA_FIRMS")
    if not key:
        raise APIKeyMissingError(
            "NASA FIRMS",
            "GEOAFRICA_FIRMS_KEY",
        )
    return key


def _parse_firms_csv(content: str, sensor: str = "") -> gpd.GeoDataFrame:
    """Parse FIRMS CSV text into a GeoDataFrame."""
    import io
    if not content.strip() or content.startswith("Sorry") or content.startswith("Error"):
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    try:
        df = pd.read_csv(io.StringIO(content))
    except Exception:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    return _df_to_geodataframe(df, sensor=sensor)


def _df_to_geodataframe(df: pd.DataFrame, sensor: str = "") -> gpd.GeoDataFrame:
    """Convert a FIRMS DataFrame to a GeoDataFrame."""
    from shapely.geometry import Point

    if "latitude" not in df.columns or "longitude" not in df.columns:
        return gpd.GeoDataFrame(df, geometry=[], crs="EPSG:4326")

    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
        crs="EPSG:4326",
    )
    gdf["sensor"] = sensor
    gdf.attrs["source"] = "NASA FIRMS — Fire Information for Resource Management System"
    gdf.attrs["credit"] = "NASA EOSDIS FIRMS (https://firms.modaps.eosdis.nasa.gov)"
    return gdf
