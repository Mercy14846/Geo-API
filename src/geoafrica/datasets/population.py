"""
GeoAfrica — Population Data Module
====================================
Merczcord Technologies Ltd.

Provides access to population grids and statistics from WorldPop and SEDAC GPW.

Data Sources
------------
- WorldPop (https://www.worldpop.org) — high-resolution gridded population
- SEDAC GPW (https://sedac.ciesin.columbia.edu/data/collection/gpw-v4)

Usage
-----
    from geoafrica import population

    # Population count grid for Nigeria (1km resolution)
    grid = population.get_grid("Nigeria", year=2020)

    # Quick statistics for an admin area
    stats = population.get_stats("Lagos", country="Nigeria", level=2)

    # Available years for a country
    years = population.available_years("Kenya")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from geoafrica.core.config import get_config
from geoafrica.core.exceptions import DataNotFoundError
from geoafrica.core.session import GeoAfricaSession

if TYPE_CHECKING:
    import xarray

_WORLDPOP_API = "https://www.worldpop.org/rest/data"
_WORLDPOP_BASE = "https://data.worldpop.org"

# Default unconstrained 1km population counts project
_DEFAULT_PROJECT = "pop"  # UN-adjusted, 100m or 1km options
_SUPPORTED_YEARS = list(range(2000, 2021))


def get_grid(
    country: str,
    year: int = 2020,
    resolution: int = 1000,
    constrained: bool = False,
) -> xarray.DataArray:
    """
    Download a WorldPop population grid raster for a country.

    Parameters
    ----------
    country : str
        Country name or ISO-2/ISO-3 code.
    year : int
        Reference year (2000–2020). Defaults to 2020.
    resolution : int
        Spatial resolution in metres: 100 or 1000. Defaults to 1000.
    constrained : bool
        If True, use constrained (built-settlement) estimates;
        otherwise use unconstrained.

    Returns
    -------
    xarray.DataArray
        Raster of population counts per grid cell.

    Examples
    --------
    >>> from geoafrica import population
    >>> da = population.get_grid("Nigeria", year=2020)
    >>> da.plot()
    """
    try:
        import rioxarray  # noqa: F401
        import xarray as xr
    except ImportError as e:
        raise ImportError(
            f"Missing dependency: {e}. Install with: pip install rioxarray xarray rasterio"
        ) from e

    from geoafrica.datasets.boundaries import _resolve_iso3

    iso3 = _resolve_iso3(country)
    iso3.lower()

    if year not in _SUPPORTED_YEARS:
        raise ValueError(f"Year must be in {_SUPPORTED_YEARS[0]}–{_SUPPORTED_YEARS[-1]}.")
    if resolution not in (100, 1000):
        raise ValueError("Resolution must be 100 or 1000 metres.")

    res_str = "1km" if resolution == 1000 else "100m"

    cfg = get_config()
    cache_path = cfg.cache_dir / "population" / f"{iso3}_{year}_{res_str}.tif"

    if not cache_path.exists():
        url = _build_worldpop_url(iso3, year, resolution, constrained)
        if url is None:
            raise DataNotFoundError(
                f"No WorldPop dataset found for '{country}' ({year}, {resolution}m).",
                query=f"{iso3}-{year}-{resolution}m",
            )
        with GeoAfricaSession() as s:
            s.download(url, str(cache_path), show_progress=True)

    da = xr.open_dataarray(cache_path, engine="rasterio")
    da.name = f"population_{year}"
    da.attrs["source"] = "WorldPop"
    da.attrs["country"] = iso3
    da.attrs["year"] = year
    da.attrs["units"] = "persons per grid cell"
    da.attrs["credit"] = (
        "WorldPop (www.worldpop.org) — School of Geography and Environmental Science, "
        "University of Southampton; Department of Geography and Geosciences, "
        "University of Louisville; Departement de Geographie, Universite de Namur) "
        "and Center for International Earth Science Information Network (CIESIN), "
        "Columbia University. CC BY 4.0."
    )
    return da


def get_stats(
    admin_name: str,
    country: str,
    level: int = 1,
    year: int = 2020,
) -> pd.DataFrame:
    """
    Return population statistics for an administrative unit.

    Clips the WorldPop raster to the admin boundary and
    computes total population, area, and density.

    Parameters
    ----------
    admin_name : str
        Name of the administrative unit (e.g. "Lagos").
    country : str
        Parent country name or ISO code.
    level : int
        Admin level (1=state/province, 2=district).
    year : int
        Reference year.

    Returns
    -------
    DataFrame with columns: admin_name, population, area_km2, density_per_km2
    """
    from geoafrica.datasets.boundaries import get_admin

    gdf = get_admin(country, level=level)
    # Try to match admin_name case-insensitively across name columns
    name_cols = [c for c in gdf.columns if "name" in c.lower()]
    mask = pd.Series([False] * len(gdf))
    for col in name_cols:
        mask |= gdf[col].str.lower().str.strip() == admin_name.lower().strip()

    if not mask.any():
        raise DataNotFoundError(
            f"Admin unit '{admin_name}' not found in {country} at level {level}.",
            query=admin_name,
        )

    admin_gdf = gdf[mask].copy()

    try:
        da = get_grid(country, year=year, resolution=1000)
        clipped = da.rio.clip(admin_gdf.geometry, da.rio.crs, drop=True, all_touched=True)
        total_pop = float(clipped.where(clipped > 0).sum().values)
    except Exception:
        total_pop = float("nan")

    # Area in km²
    admin_proj = admin_gdf.to_crs(epsg=6933)  # Equal-area
    area_km2 = float(admin_proj.geometry.area.sum() / 1e6)
    density = total_pop / area_km2 if area_km2 > 0 else float("nan")

    return pd.DataFrame(
        [
            {
                "admin_name": admin_name,
                "country": country,
                "admin_level": level,
                "year": year,
                "population": round(total_pop),
                "area_km2": round(area_km2, 2),
                "density_per_km2": round(density, 2),
                "source": "WorldPop UN-adjusted",
            }
        ]
    )


def available_years(country: str) -> list[int]:
    """
    Return the list of years with available WorldPop data for *country*.

    Returns
    -------
    list[int]
    """
    from geoafrica.datasets.boundaries import _resolve_iso3

    iso3 = _resolve_iso3(country)

    with GeoAfricaSession() as s:
        try:
            resp = s.get(
                f"{_WORLDPOP_API}/pop",
                params={"iso3": iso3, "popyear": "all"},
            )
            data = resp.json()
            years = sorted(
                {int(d.get("popyear", 0)) for d in data.get("data", []) if d.get("popyear")}
            )
            return years if years else _SUPPORTED_YEARS
        except Exception:
            return _SUPPORTED_YEARS


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_worldpop_url(
    iso3: str,
    year: int,
    resolution: int,
    constrained: bool,
) -> str | None:
    """Query the WorldPop REST API for a direct download URL."""
    res_str = "1km" if resolution == 1000 else "100m"
    constrained_str = "constrained" if constrained else "unconstrained"

    with GeoAfricaSession() as s:
        try:
            resp = s.get(
                f"{_WORLDPOP_API}/pop",
                params={
                    "iso3": iso3,
                    "popyear": year,
                    "project": f"pop_{constrained_str}",
                },
            )
            data = resp.json().get("data", [])
        except Exception:
            data = []

    # Find GeoTIFF at requested resolution
    for item in data:
        for file_info in item.get("files", []):
            file_url = file_info.get("url", "")
            if res_str in file_url and file_url.endswith(".tif"):
                return file_url

    # Fallback: construct direct URL pattern
    iso3_lower = iso3.lower()
    direct = (
        f"{_WORLDPOP_BASE}/GIS/Population/Global_2000_2020/"
        f"{year}/{iso3}/{iso3_lower}_ppp_{year}_1km_Aggregated_UNadj.tif"
    )
    with GeoAfricaSession() as s:
        try:
            r = s._session.head(direct, timeout=10)
            if r.status_code == 200:
                return direct
        except Exception:
            pass

    return None
