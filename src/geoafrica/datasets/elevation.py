"""
GeoAfrica — Elevation & Terrain Module
=========================================
Merczcord Technologies Ltd.

Access global Digital Elevation Models (DEMs) from multiple sources:
SRTM 30m, Copernicus DEM 30m, and AW3D30.

Data Sources
------------
- OpenTopography REST API (https://portal.opentopography.org/apidocs/)
  Optional API key: https://portal.opentopography.org/requestApiKey
- SRTM via NASA EarthData (public, no key)
- Copernicus DEM 30m (open, via AWS/Azure)

Usage
-----
    from geoafrica import elevation

    # DEM for Rwanda
    dem = elevation.get_dem("Rwanda", source="SRTMGL1")

    # Terrain profile between two points
    profile = elevation.terrain_profile(
        start=(29.36, -1.94),   # (lon, lat)
        end=(30.05, -1.55),
        num_points=200,
    )

    # Slope and aspect from DEM
    slope, aspect = elevation.compute_slope_aspect(dem)

    # Watershed delineation (simple)
    watershed = elevation.viewshed(dem, observer=(29.5, -1.9), radius_km=10)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import xarray

from geoafrica.core.config import get_config
from geoafrica.core.exceptions import InvalidBoundingBoxError
from geoafrica.core.session import GeoAfricaSession

_OPENTOPO_API = "https://portal.opentopography.org/API/globaldem"

DEM_SOURCES = {
    "SRTMGL3": "SRTM GL3 (90m)",
    "SRTMGL1": "SRTM GL1 (30m)",
    "SRTMGL1_E": "SRTM GL1 Ellipsoidal (30m)",
    "AW3D30": "ALOS World 3D 30m",
    "AW3D30_E": "ALOS World 3D 30m Ellipsoidal",
    "COP30": "Copernicus DEM GLO-30 (30m)",
    "COP90": "Copernicus DEM GLO-90 (90m)",
    "NASADEM": "NASA DEM (30m)",
    "EU_DTM": "European DTM (30m)",
}


def get_dem(
    country: str,
    source: str = "SRTMGL1",
    output_format: str = "GTiff",
) -> "xarray.DataArray":
    """
    Download a Digital Elevation Model raster for a country.

    Parameters
    ----------
    country : str
        Country name or ISO code.
    source : str
        DEM product. Options: SRTMGL1, SRTMGL3, COP30, AW3D30, NASADEM.
        Default: SRTMGL1 (SRTM 30m).
    output_format : str
        Output format: 'GTiff'. AAIGrid also supported.

    Returns
    -------
    xarray.DataArray
        Elevation raster in metres above sea level.

    Examples
    --------
    >>> dem = elevation.get_dem("Rwanda", source="COP30")
    >>> dem.plot(cmap="terrain")
    """
    if source not in DEM_SOURCES:
        raise ValueError(
            f"Unknown DEM source '{source}'. "
            f"Available: {list(DEM_SOURCES)}"
        )

    from geoafrica.datasets.boundaries import get_bbox
    bbox = get_bbox(country)
    return get_dem_bbox(bbox, source=source, output_format=output_format)


def get_dem_bbox(
    bbox: list[float],
    source: str = "SRTMGL1",
    output_format: str = "GTiff",
) -> "xarray.DataArray":
    """
    Download a DEM for a bounding box.

    Parameters
    ----------
    bbox : list of float
        [min_lon, min_lat, max_lon, max_lat]
    source : str
        DEM product code.
    output_format : str
        'GTiff'.

    Returns
    -------
    xarray.DataArray
    """
    import rioxarray  # noqa: F401
    import xarray as xr

    if len(bbox) != 4:
        raise InvalidBoundingBoxError(bbox)

    min_lon, min_lat, max_lon, max_lat = bbox
    cfg = get_config()

    label = f"{source}_{min_lon:.2f}_{min_lat:.2f}_{max_lon:.2f}_{max_lat:.2f}"
    cache_path = cfg.cache_dir / "elevation" / f"{label}.tif"

    if not cache_path.exists():
        url = _build_opentopo_url(bbox, source, output_format, cfg)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with GeoAfricaSession() as s:
            s.download(url, str(cache_path), show_progress=True)

    da = xr.open_dataarray(cache_path, engine="rasterio")
    if da.rio.crs is None:
        da = da.rio.write_crs("EPSG:4326")

    da.name = "elevation_m"
    da.attrs["source"] = DEM_SOURCES.get(source, source)
    da.attrs["units"] = "metres above sea level"
    da.attrs["credit"] = "OpenTopography (https://opentopography.org)"
    return da


def terrain_profile(
    start: tuple[float, float],
    end: tuple[float, float],
    num_points: int = 100,
    source: str = "SRTMGL1",
) -> pd.DataFrame:
    """
    Extract an elevation profile along a transect between two points.

    Parameters
    ----------
    start : tuple of (lon, lat)
        Start coordinate.
    end : tuple of (lon, lat)
        End coordinate.
    num_points : int
        Number of sample points along the transect.
    source : str
        DEM source.

    Returns
    -------
    DataFrame with columns: distance_km, elevation_m, lon, lat

    Examples
    --------
    >>> profile = elevation.terrain_profile(
    ...     start=(36.8, 3.8),   # Addis Ababa area
    ...     end=(38.7, 6.1),
    ... )
    >>> profile.plot(x="distance_km", y="elevation_m")
    """

    start_lon, start_lat = start
    end_lon, end_lat = end

    lons = np.linspace(start_lon, end_lon, num_points)
    lats = np.linspace(start_lat, end_lat, num_points)

    bbox = [
        min(lons) - 0.05, min(lats) - 0.05,
        max(lons) + 0.05, max(lats) + 0.05,
    ]
    dem = get_dem_bbox(bbox, source=source)

    elevations = []
    for lon, lat in zip(lons, lats):
        try:
            val = float(dem.sel(x=lon, y=lat, method="nearest").values)
            if val < -9990:
                val = float("nan")
        except Exception:
            val = float("nan")
        elevations.append(val)

    # Compute cumulative distance in km
    from pyproj import Geod
    geod = Geod(ellps="WGS84")
    distances = [0.0]
    for i in range(1, num_points):
        _, _, dist = geod.inv(lons[i - 1], lats[i - 1], lons[i], lats[i])
        distances.append(distances[-1] + dist / 1000)

    return pd.DataFrame({
        "distance_km": distances,
        "elevation_m": elevations,
        "lon": lons,
        "lat": lats,
    })


def compute_slope_aspect(
    dem: "xarray.DataArray",
) -> "tuple[xarray.DataArray, xarray.DataArray]":
    """
    Compute slope (degrees) and aspect (degrees from north) from a DEM.

    Parameters
    ----------
    dem : xarray.DataArray
        Elevation raster as returned by get_dem().

    Returns
    -------
    tuple of (slope, aspect) — both xarray.DataArrays in degrees.
    """

    data = dem.squeeze().values.astype(float)
    data[data < -9990] = np.nan

    # Cell size in metres (approximate)
    lat_center = float(dem.y.mean())
    lon_res = abs(float(dem.x.diff("x").mean()))
    lat_res = abs(float(dem.y.diff("y").mean()))

    dx = lon_res * np.cos(np.radians(lat_center)) * 111320  # metres
    dy = lat_res * 111320

    dz_dx = np.gradient(data, axis=1) / dx
    dz_dy = np.gradient(data, axis=0) / dy

    slope_rad = np.arctan(np.sqrt(dz_dx ** 2 + dz_dy ** 2))
    aspect_rad = np.arctan2(-dz_dx, dz_dy)

    slope_deg = np.degrees(slope_rad)
    aspect_deg = (np.degrees(aspect_rad) + 360) % 360

    slope_da = dem.copy(data=slope_deg[np.newaxis, :, :] if dem.ndim == 3 else slope_deg)
    slope_da.name = "slope_degrees"
    slope_da.attrs["units"] = "degrees"

    aspect_da = dem.copy(data=aspect_deg[np.newaxis, :, :] if dem.ndim == 3 else aspect_deg)
    aspect_da.name = "aspect_degrees"
    aspect_da.attrs["units"] = "degrees from north"

    return slope_da, aspect_da


def list_sources() -> pd.DataFrame:
    """Return a DataFrame listing available DEM data sources."""
    rows = [{"code": k, "description": v} for k, v in DEM_SOURCES.items()]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_opentopo_url(
    bbox: list[float],
    source: str,
    output_format: str,
    cfg,
) -> str:
    """Build the OpenTopography API URL."""
    min_lon, min_lat, max_lon, max_lat = bbox
    api_key = cfg.get_api_key("OPENTOPODATA") or "demoapikeyot2022"  # public demo key

    params = (
        f"?demtype={source}"
        f"&south={min_lat}&north={max_lat}"
        f"&west={min_lon}&east={max_lon}"
        f"&outputFormat={output_format}"
        f"&API_Key={api_key}"
    )
    return _OPENTOPO_API + params
