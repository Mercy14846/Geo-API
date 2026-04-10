"""
GeoAfrica — Humanitarian Data Module
=======================================
Merczcord Technologies Ltd.

Access thousands of humanitarian datasets from the UN OCHA
Humanitarian Data Exchange (HDX) using the official HDX Python API.

Data Sources
------------
- HDX / CKAN (https://data.humdata.org) — UN OCHA

Usage
-----
    from geoafrica import humanitarian

    # Search for datasets
    results = humanitarian.search("Nigeria flood 2024")

    # Get a specific dataset by ID or name
    ds = humanitarian.get_dataset("cod-ab-nga")

    # Download resources from a dataset
    files = humanitarian.download_dataset("cod-ab-nga", output_dir="./data")

    # List organisations/providers on HDX
    orgs = humanitarian.list_organizations()

    # Get resources for a country
    country_data = humanitarian.get_country_datasets("Nigeria", rows=20)
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from geoafrica.core.config import get_config
from geoafrica.core.exceptions import DataNotFoundError

_HDX_CONFIGURED = False


def _ensure_hdx() -> None:
    """Initialize the HDX Configuration singleton."""
    global _HDX_CONFIGURED
    if _HDX_CONFIGURED:
        return
    try:
        from hdx.hdx_configuration import Configuration
        Configuration.create(
            hdx_site="prod",
            user_agent="GeoAfrica-SDK/0.2.0 (Merczcord Technologies Ltd.)",
            hdx_read_only=True,
        )
        _HDX_CONFIGURED = True
    except Exception:
        # May already be configured
        _HDX_CONFIGURED = True


def search(
    query: str,
    rows: int = 10,
    organization: str | None = None,
    location: str | None = None,
) -> pd.DataFrame:
    """
    Search for datasets on the Humanitarian Data Exchange.

    Parameters
    ----------
    query : str
        Search keywords (e.g. "Nigeria flood 2024", "Kenya drought").
    rows : int
        Maximum results to return. Default 10.
    organization : str, optional
        Filter by HDX organization (e.g. 'ocha-nigeria').
    location : str, optional
        Filter by country/location.

    Returns
    -------
    DataFrame with columns: title, name, organization, date_modified, url

    Examples
    --------
    >>> results = humanitarian.search("East Africa displacement")
    >>> results[["title","organization","date_modified"]].head()
    """
    _ensure_hdx()
    from hdx.data.dataset import Dataset

    filter_dict = {}
    if organization:
        filter_dict["organization"] = organization
    if location:
        filter_dict["groups"] = location

    datasets = Dataset.search_in_hdx(query, rows=rows, **filter_dict)

    records = []
    for ds in datasets:
        records.append({
            "title": ds.get("title", ""),
            "name": ds.get("name", ""),
            "organization": ds.get_organization().get("title", "") if ds.get("organization") else "",
            "date_modified": ds.get("last_modified", ""),
            "date_created": ds.get("metadata_created", ""),
            "num_resources": ds.get("num_resources", 0),
            "license": ds.get("license_title", ""),
            "url": f"https://data.humdata.org/dataset/{ds.get('name', '')}",
            "hdx_id": ds.get("id", ""),
        })

    return pd.DataFrame(records)


def get_dataset(dataset_id: str) -> pd.DataFrame:
    """
    Retrieve metadata for a specific HDX dataset.

    Parameters
    ----------
    dataset_id : str
        HDX dataset name or ID (e.g. 'cod-ab-nga').

    Returns
    -------
    DataFrame listing all resources in the dataset.
    """
    _ensure_hdx()
    from hdx.data.dataset import Dataset

    try:
        ds = Dataset.read_from_hdx(dataset_id)
    except Exception:
        raise DataNotFoundError(
            f"Dataset '{dataset_id}' not found on HDX.",
            query=dataset_id,
        )

    records = []
    for resource in ds.get_resources():
        records.append({
            "resource_name": resource.get("name", ""),
            "resource_id": resource.get("id", ""),
            "format": resource.get("format", ""),
            "size_bytes": resource.get("size", 0),
            "url": resource.get("url", ""),
            "description": resource.get("description", ""),
            "last_modified": resource.get("last_modified", ""),
        })

    return pd.DataFrame(records)


def download_dataset(
    dataset_id: str,
    output_dir: str | None = None,
    resource_format: str | None = None,
) -> list[str]:
    """
    Download all (or filtered) resources from an HDX dataset.

    Parameters
    ----------
    dataset_id : str
        HDX dataset name or ID.
    output_dir : str, optional
        Directory to save files. Defaults to ~/.geoafrica/cache/humanitarian/
    resource_format : str, optional
        Filter by file format (e.g. 'SHP', 'CSV', 'XLSX', 'GEOJSON').

    Returns
    -------
    list of str
        Absolute paths to downloaded files.

    Examples
    --------
    >>> files = humanitarian.download_dataset("cod-ab-nga", resource_format="SHP")
    """
    _ensure_hdx()
    from hdx.data.dataset import Dataset

    cfg = get_config()
    dest_dir = Path(output_dir) if output_dir else cfg.cache_dir / "humanitarian" / dataset_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        ds = Dataset.read_from_hdx(dataset_id)
    except Exception:
        raise DataNotFoundError(f"Dataset '{dataset_id}' not found on HDX.")

    resources = ds.get_resources()
    if resource_format:
        resources = [r for r in resources if r.get("format", "").upper() == resource_format.upper()]

    downloaded = []
    for resource in resources:
        try:
            _, path = resource.download(folder=str(dest_dir))
            downloaded.append(str(Path(path).resolve()))
        except Exception as e:
            print(f"Warning: Could not download {resource.get('name')}: {e}")

    return downloaded


def get_country_datasets(
    country: str,
    rows: int = 20,
    data_type: str | None = None,
) -> pd.DataFrame:
    """
    List HDX datasets for a specific country.

    Parameters
    ----------
    country : str
        Country name or ISO code (e.g. 'Nigeria', 'NGA').
    rows : int
        Max results.
    data_type : str, optional
        Filter by HDX tag (e.g. 'health', 'population', 'displacement', 'flood').

    Returns
    -------
    DataFrame of datasets.
    """
    query = country if not data_type else f"{country} {data_type}"
    return search(query, rows=rows, location=country.lower()[:3])


def list_organizations(limit: int = 50) -> pd.DataFrame:
    """
    Return a DataFrame listing HDX organizations.

    Parameters
    ----------
    limit : int
        Maximum number of organizations to return.

    Returns
    -------
    DataFrame with: name, title, packages (dataset count)
    """
    _ensure_hdx()
    from hdx.data.organization import Organization

    try:
        orgs = Organization.get_all_organization_names(include_extras=True)
        records = [{"name": o} for o in (orgs or [])[:limit]]
        return pd.DataFrame(records)
    except Exception:
        return pd.DataFrame(columns=["name", "title"])


def load_geospatial(
    dataset_id: str,
    resource_index: int = 0,
) -> gpd.GeoDataFrame:
    """
    Download and load the first geospatial resource from an HDX dataset.

    Parameters
    ----------
    dataset_id : str
        HDX dataset name or ID.
    resource_index : int
        Index of the resource to load. Default 0 (first resource).

    Returns
    -------
    GeoDataFrame
    """
    files = download_dataset(dataset_id)
    if not files:
        raise DataNotFoundError(f"No files downloaded for dataset '{dataset_id}'.")

    # Find a shapefile or GeoJSON
    geo_exts = {".shp", ".geojson", ".gpkg", ".json"}
    geo_files = [f for f in files if Path(f).suffix.lower() in geo_exts]
    if not geo_files:
        raise DataNotFoundError(
            f"No geospatial files found in dataset '{dataset_id}'. "
            f"Available: {[Path(f).name for f in files]}"
        )

    return gpd.read_file(geo_files[resource_index])
