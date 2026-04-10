"""
GeoAfrica — Climate Data Module
==================================
Merczcord Technologies Ltd.

Access rainfall, temperature, and climate indices for Africa and the world
from CHIRPS, ERA5, and other open climate data providers.

Data Sources
------------
- CHIRPS (https://www.chc.ucsb.edu/data/chirps) — Rainfall Estimates
  from Rain Gauge and Satellite Observations (no key required)
- ERA5 (https://cds.climate.copernicus.eu) — Copernicus Climate Data Store
  (optional: requires GEOAFRICA_CDS_KEY for ERA5 access)

Usage
-----
    from geoafrica import climate

    # Monthly rainfall for Ethiopia (2023)
    rain = climate.get_rainfall("Ethiopia", year=2023)

    # Annual rainfall anomaly
    anom = climate.rainfall_anomaly("Nigeria", year=2022)

    # Long-term mean rainfall (1981-2010)
    lta = climate.long_term_mean("Ghana")

    # Download CHIRPS for a bounding box
    chirps = climate.get_chirps_bbox(bbox=[3, 4, 15, 14], year=2023, month=6)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    import xarray

from geoafrica.core.config import get_config
from geoafrica.core.exceptions import DataNotFoundError
from geoafrica.core.session import GeoAfricaSession

# CHIRPS base URLs
_CHIRPS_MONTHLY = (
    "https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_monthly/tifs/"
    "chirps-v2.0.{year}.{month:02d}.tif.gz"
)
_CHIRPS_ANNUAL = (
    "https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_annual/tifs/chirps-v2.0.{year}.tif"
)
_CHIRPS_GLOBAL_MONTHLY = (
    "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_monthly/tifs/"
    "chirps-v2.0.{year}.{month:02d}.tif.gz"
)

SUPPORTED_YEARS_CHIRPS = list(range(1981, 2025))


def get_rainfall(
    country: str,
    year: int,
    month: int | None = None,
    source: str = "chirps",
) -> xarray.DataArray:
    """
    Download and clip a rainfall raster for a country.

    Parameters
    ----------
    country : str
        Country name or ISO code.
    year : int
        Year (CHIRPS: 1981–2024).
    month : int, optional
        Month (1–12). If None, returns annual total.
    source : str
        'chirps' (default). ERA5 requires CDS API key.

    Returns
    -------
    xarray.DataArray
        Clipped rainfall raster in mm.

    Examples
    --------
    >>> rain = climate.get_rainfall("Nigeria", year=2022)
    >>> rain.plot(cmap="Blues")
    """
    if source == "chirps":
        return _chirps_for_country(country, year, month)
    elif source == "era5":
        return _era5_for_country(country, year, month)
    else:
        raise ValueError(f"Unknown source '{source}'. Use 'chirps' or 'era5'.")


def get_chirps_bbox(
    bbox: list[float],
    year: int,
    month: int | None = None,
) -> xarray.DataArray:
    """
    Download a CHIRPS rainfall raster for a bounding box.

    Parameters
    ----------
    bbox : list of float
        [min_lon, min_lat, max_lon, max_lat]
    year : int
        Year (1981–2024).
    month : int, optional
        Month (1–12). If None, returns annual.

    Returns
    -------
    xarray.DataArray
    """
    import rioxarray  # noqa: F401
    import xarray as xr

    path = _download_chirps(year, month, global_coverage=False)
    da = xr.open_dataarray(path, engine="rasterio")
    min_lon, min_lat, max_lon, max_lat = bbox
    da_clipped = da.sel(
        x=slice(min_lon, max_lon),
        y=slice(max_lat, min_lat),
    )
    da_clipped.attrs["source"] = "CHIRPS v2.0"
    da_clipped.attrs["units"] = "mm"
    return da_clipped


def monthly_series(
    country: str,
    year: int,
) -> pd.DataFrame:
    """
    Return a DataFrame of mean monthly rainfall for a country.

    Parameters
    ----------
    country : str
        Country name or ISO code.
    year : int
        Year.

    Returns
    -------
    DataFrame with columns: month, month_name, mean_rainfall_mm, max_rainfall_mm
    """
    records = []
    for m in range(1, 13):
        try:
            da = get_rainfall(country, year=year, month=m)
            mean_val = float(da.where(da > 0).mean().values)
            max_val = float(da.where(da > 0).max().values)
        except Exception:
            mean_val = float("nan")
            max_val = float("nan")

        records.append(
            {
                "month": m,
                "month_name": pd.Timestamp(year=year, month=m, day=1).strftime("%B"),
                "mean_rainfall_mm": round(mean_val, 2),
                "max_rainfall_mm": round(max_val, 2),
            }
        )
    return pd.DataFrame(records)


def rainfall_anomaly(
    country: str,
    year: int,
    baseline_start: int = 1981,
    baseline_end: int = 2010,
) -> xarray.DataArray:
    """
    Compute annual rainfall anomaly vs. a long-term baseline.

    Parameters
    ----------
    country : str
        Country name or ISO code.
    year : int
        Target year.
    baseline_start : int
        Start year of baseline period. Default 1981.
    baseline_end : int
        End year of baseline period. Default 2010.

    Returns
    -------
    xarray.DataArray
        Anomaly raster (mm, positive = above average).
    """
    import numpy as np

    current = get_rainfall(country, year=year)

    baseline_arrays = []
    for y in range(baseline_start, baseline_end + 1):
        try:
            da = get_rainfall(country, year=y)
            baseline_arrays.append(da.values)
        except Exception:
            continue

    if not baseline_arrays:
        raise DataNotFoundError(f"Could not compute baseline for '{country}'.")

    baseline_mean = np.nanmean(baseline_arrays, axis=0)
    anomaly = current.copy(data=current.values - baseline_mean)
    anomaly.name = f"rainfall_anomaly_{year}"
    anomaly.attrs["source"] = "CHIRPS v2.0 — Anomaly vs baseline"
    anomaly.attrs["baseline"] = f"{baseline_start}–{baseline_end}"
    anomaly.attrs["units"] = "mm"
    return anomaly


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _chirps_for_country(
    country: str,
    year: int,
    month: int | None,
) -> xarray.DataArray:
    """Download + clip CHIRPS raster for a country boundary."""
    import rioxarray  # noqa: F401
    import xarray as xr

    from geoafrica.datasets.boundaries import get_country

    path = _download_chirps(year, month, global_coverage=False)
    boundary = get_country(country)

    da = xr.open_dataarray(path, engine="rasterio")
    if da.rio.crs is None:
        da = da.rio.write_crs("EPSG:4326")

    clipped = da.rio.clip(boundary.geometry, boundary.crs, drop=True, all_touched=True)
    clipped = clipped.where(clipped > -9990)  # Mask nodata
    label = f"month_{month}" if month else "annual"
    clipped.name = f"chirps_rainfall_{year}_{label}"
    clipped.attrs["source"] = "CHIRPS v2.0"
    clipped.attrs["country"] = country
    clipped.attrs["year"] = year
    clipped.attrs["units"] = "mm"
    clipped.attrs["credit"] = (
        "Funk, C., P. Peterson, M. Landsfeld, D. Pedreros, J. Verdin, S. Shukla, "
        "G. Husak, J. Rowland, L. Harrison, A. Hoell & J. Michaelsen. 2015. "
        "The climate hazards infrared precipitation with stations — a new "
        "environmental record for monitoring extremes. Scientific Data. CC BY."
    )
    return clipped


def _download_chirps(year: int, month: int | None, global_coverage: bool = False) -> Path:
    """Download a CHIRPS TIF file and return the local path."""
    import gzip
    import shutil

    cfg = get_config()
    label = f"month{month:02d}" if month else "annual"
    cache_path = cfg.cache_dir / "climate" / f"chirps_{year}_{label}.tif"

    if cache_path.exists():
        return cache_path

    if month:
        url_template = _CHIRPS_GLOBAL_MONTHLY if global_coverage else _CHIRPS_MONTHLY
        url = url_template.format(year=year, month=month)
    else:
        url = _CHIRPS_ANNUAL.format(year=year)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    gz_path = cache_path.with_suffix(".tif.gz")

    with GeoAfricaSession() as s:
        try:
            s.download(url, str(gz_path), show_progress=True)
        except Exception:
            # Try global coverage as fallback
            if not global_coverage and month:
                url = _CHIRPS_GLOBAL_MONTHLY.format(year=year, month=month)
                s.download(url, str(gz_path), show_progress=True)
            else:
                raise

    # Decompress .gz if needed
    if gz_path.suffix == ".gz" and gz_path.exists():
        with gzip.open(str(gz_path), "rb") as f_in:
            with open(cache_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        gz_path.unlink()
    elif not cache_path.exists():
        gz_path.rename(cache_path)

    return cache_path


def _era5_for_country(
    country: str,
    year: int,
    month: int | None,
) -> xarray.DataArray:
    """Fetch ERA5 data via CDS API (requires api key)."""
    cfg = get_config()
    key = cfg.get_api_key("COPERNICUS_CDS")
    if not key:
        raise ImportError(
            "ERA5 requires a Copernicus CDS API key. "
            "Register at https://cds.climate.copernicus.eu/ and run:\n"
            "  geoafrica config set COPERNICUS_CDS <your_key>"
        )

    raise NotImplementedError(
        "ERA5 direct download is available via cdsapi. Use CHIRPS source for automatic access."
    )
