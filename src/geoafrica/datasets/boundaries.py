"""
GeoAfrica — Administrative Boundaries Module
=============================================
Merczcord Technologies Ltd.

Provides easy access to administrative boundary data at multiple levels
for any country in the world, with special focus on African nations.

Data Sources
------------
- GADM (https://gadm.org) — Global Administrative Areas
- HDX (https://data.humdata.org) — UN OCHA Humanitarian Data Exchange
- Overture Maps Divisions — High-quality open map data

Usage
-----
    from geoafrica import boundaries

    # Get country outline
    ng = boundaries.get_country("Nigeria")

    # Get states / provinces (level 1)
    states = boundaries.get_admin("Nigeria", level=1)

    # Get a specific sub-admin unit
    lagos = boundaries.get_admin("Lagos", country="Nigeria", level=2)

    # List all available countries
    countries = boundaries.list_countries()

    # Search by ISO code
    gh = boundaries.get_by_iso("GH", level=0)
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

from geoafrica.core.config import get_config
from geoafrica.core.exceptions import DataNotFoundError
from geoafrica.core.session import GeoAfricaSession

# ---------------------------------------------------------------------------
# GADM — base URL for GeoJSON API
# ---------------------------------------------------------------------------
_GADM_GEOJSON_URL = "https://gadm.org/json/gadm41_{iso}_{level}.json"
_GADM_GPKG_URL = "https://geodata.ucdavis.edu/gadm/gadm4.1/gpkg/gadm41_{iso}.gpkg"
_GEOFABRIK_INDEX = "https://download.geofabrik.de/index-v1.json"

# ISO-3166 alpha-2 → alpha-3 quick lookup for common African nations
_ISO2_TO_ISO3: dict[str, str] = {
    "DZ": "DZA", "AO": "AGO", "BJ": "BEN", "BW": "BWA", "BF": "BFA",
    "BI": "BDI", "CV": "CPV", "CM": "CMR", "CF": "CAF", "TD": "TCD",
    "KM": "COM", "CG": "COG", "CD": "COD", "CI": "CIV", "DJ": "DJI",
    "EG": "EGY", "GQ": "GNQ", "ER": "ERI", "SZ": "SWZ", "ET": "ETH",
    "GA": "GAB", "GM": "GMB", "GH": "GHA", "GN": "GIN", "GW": "GNB",
    "KE": "KEN", "LS": "LSO", "LR": "LBR", "LY": "LBY", "MG": "MDG",
    "MW": "MWI", "ML": "MLI", "MR": "MRT", "MU": "MUS", "MA": "MAR",
    "MZ": "MOZ", "NA": "NAM", "NE": "NER", "NG": "NGA", "RW": "RWA",
    "ST": "STP", "SN": "SEN", "SL": "SLE", "SO": "SOM", "ZA": "ZAF",
    "SS": "SSD", "SD": "SDN", "TZ": "TZA", "TG": "TGO", "TN": "TUN",
    "UG": "UGA", "ZM": "ZMB", "ZW": "ZWE",
    # Other major countries
    "US": "USA", "GB": "GBR", "FR": "FRA", "DE": "DEU", "IN": "IND",
    "CN": "CHN", "BR": "BRA", "AU": "AUS", "CA": "CAN", "JP": "JPN",
    "MX": "MEX", "ID": "IDN", "PK": "PAK", "BD": "BGD",
}

# Country name → ISO-2 code lookup
_COUNTRY_NAME_TO_ISO2: dict[str, str] = {
    "nigeria": "NG", "ghana": "GH", "kenya": "KE", "ethiopia": "ET",
    "tanzania": "TZ", "uganda": "UG", "south africa": "ZA", "egypt": "EG",
    "cameroon": "CM", "senegal": "SN", "mali": "ML", "niger": "NE",
    "burkina faso": "BF", "ivory coast": "CI", "cote d'ivoire": "CI",
    "mozambique": "MZ", "rwanda": "RW", "zambia": "ZM", "zimbabwe": "ZW",
    "malawi": "MW", "angola": "AO", "namibia": "NA", "botswana": "BW",
    "libya": "LY", "tunisia": "TN", "morocco": "MA", "algeria": "DZ",
    "somalia": "SO", "sudan": "SD", "chad": "TD", "gabon": "GA",
    "guinea": "GN", "sierra leone": "SL", "liberia": "LR", "togo": "TG",
    "benin": "BJ", "drc": "CD", "congo": "CG", "eritrea": "ER",
    "djibouti": "DJ", "lesotho": "LS", "eswatini": "SZ",
    "united states": "US", "usa": "US", "uk": "GB", "united kingdom": "GB",
    "france": "FR", "germany": "DE", "india": "IN", "china": "CN",
    "brazil": "BR", "australia": "AU", "canada": "CA", "japan": "JP",
}


def _resolve_iso3(country: str) -> str:
    """Resolve a country name or ISO code to ISO-3166 alpha-3."""
    c = country.strip()

    # Already ISO-3 (e.g. "NGA")
    if len(c) == 3 and c.isupper():
        return c

    # ISO-2 → ISO-3
    if len(c) == 2 and c.upper() in _ISO2_TO_ISO3:
        return _ISO2_TO_ISO3[c.upper()]

    # Full name
    iso2 = _COUNTRY_NAME_TO_ISO2.get(c.lower())
    if iso2 and iso2 in _ISO2_TO_ISO3:
        return _ISO2_TO_ISO3[iso2]

    raise DataNotFoundError(
        f"Could not resolve '{country}' to an ISO country code. "
        "Use a full country name (e.g. 'Nigeria') or ISO-2/ISO-3 code.",
        query=country,
    )


def get_country(
    country: str,
    source: str = "gadm",
    crs: str = "EPSG:4326",
) -> gpd.GeoDataFrame:
    """
    Return the level-0 (country outline) boundary as a GeoDataFrame.

    Parameters
    ----------
    country : str
        Country name (e.g. "Nigeria") or ISO-2/ISO-3 code.
    source : str
        Data source: 'gadm' (default) or 'hdx'.
    crs : str
        Output CRS. Defaults to WGS84 (EPSG:4326).

    Returns
    -------
    GeoDataFrame

    Examples
    --------
    >>> from geoafrica import boundaries
    >>> ng = boundaries.get_country("Nigeria")
    >>> ng.plot()
    """
    return get_admin(country, level=0, source=source, crs=crs)


def get_admin(
    country: str,
    level: int = 1,
    source: str = "gadm",
    crs: str = "EPSG:4326",
) -> gpd.GeoDataFrame:
    """
    Return administrative boundaries at the specified level.

    Parameters
    ----------
    country : str
        Country name or ISO code.
    level : int
        Admin level:
          0 = Country outline
          1 = States / Provinces
          2 = Districts / Counties
          3 = Sub-districts (where available)
    source : str
        'gadm' (default) or 'hdx'.
    crs : str
        Output CRS.

    Returns
    -------
    GeoDataFrame

    Examples
    --------
    >>> states = boundaries.get_admin("Kenya", level=1)
    >>> districts = boundaries.get_admin("Nigeria", level=2)
    """
    iso3 = _resolve_iso3(country)

    if source == "gadm":
        return _fetch_gadm(iso3, level, crs)
    elif source == "hdx":
        return _fetch_hdx_boundaries(iso3, level, crs)
    else:
        raise ValueError(f"Unknown source '{source}'. Choose 'gadm' or 'hdx'.")


def get_by_iso(
    iso_code: str,
    level: int = 0,
    source: str = "gadm",
) -> gpd.GeoDataFrame:
    """
    Fetch boundaries using an ISO-2 or ISO-3 country code directly.

    Parameters
    ----------
    iso_code : str
        ISO-3166 alpha-2 (e.g. 'GH') or alpha-3 (e.g. 'GHA').
    level : int
        Admin level (0–3).
    source : str
        'gadm' or 'hdx'.

    Returns
    -------
    GeoDataFrame
    """
    return get_admin(iso_code, level=level, source=source)


def list_countries(region: str | None = None) -> pd.DataFrame:
    """
    Return a DataFrame of supported countries.

    Parameters
    ----------
    region : str, optional
        Filter by region: 'africa', 'asia', 'europe', 'americas', 'oceania'.

    Returns
    -------
    DataFrame with columns: country, iso2, iso3, region
    """
    rows = []
    for name, iso2 in _COUNTRY_NAME_TO_ISO2.items():
        iso3 = _ISO2_TO_ISO3.get(iso2, "")
        # Determine rough region from iso2
        _region = _iso2_region(iso2)
        rows.append({"country": name.title(), "iso2": iso2, "iso3": iso3, "region": _region})

    df = pd.DataFrame(rows).drop_duplicates(subset=["iso2"]).sort_values("country").reset_index(drop=True)
    if region:
        df = df[df["region"].str.lower() == region.lower()].reset_index(drop=True)
    return df


def get_bbox(country: str) -> list[float]:
    """
    Return the bounding box [min_lon, min_lat, max_lon, max_lat] for a country.

    Examples
    --------
    >>> bbox = boundaries.get_bbox("Nigeria")
    >>> # [2.6917, 4.2406, 14.6799, 13.8659]
    """
    gdf = get_country(country)
    bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
    return list(bounds)


# ---------------------------------------------------------------------------
# Internal fetch functions
# ---------------------------------------------------------------------------

def _fetch_gadm(iso3: str, level: int, crs: str) -> gpd.GeoDataFrame:
    """Download and parse GADM GeoPackage for a given ISO-3 code and admin level."""
    cfg = get_config()
    cache_gpkg = cfg.cache_dir / "boundaries" / f"gadm41_{iso3}.gpkg"

    if not cache_gpkg.exists():
        url = _GADM_GPKG_URL.format(iso=iso3)
        with GeoAfricaSession() as s:
            try:
                s.download(url, str(cache_gpkg), show_progress=True)
            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code == 404:
                    raise DataNotFoundError(
                        f"No GADM data found for '{iso3}'.",
                        query=iso3,
                    )
                raise

    # GADM 4.1 GeoPackages typically have layers named ADM_0, ADM_1, etc.
    possible_layers = [f"ADM_{level}", f"ADM_ADM_{level}", f"gadm41_{iso3}_{level}"]
    gdf = None
    last_err = None

    for layer in possible_layers:
        try:
            gdf = gpd.read_file(cache_gpkg, layer=layer)
            break
        except Exception as e:
            last_err = e
            continue

    if gdf is None:
        raise DataNotFoundError(
            f"Level {level} data not found for '{iso3}' in GADM GeoPackage. "
            f"Are you sure this level exists? (Details: {last_err})",
            query=f"{iso3}-level{level}",
        )

    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")

    return gdf.to_crs(crs)


def _fetch_hdx_boundaries(iso3: str, level: int, crs: str) -> gpd.GeoDataFrame:
    """Fetch boundaries from HDX using the hdx-python-api."""
    try:
        from hdx.data.dataset import Dataset
        from hdx.hdx_configuration import Configuration
    except ImportError:
        raise ImportError(
            "hdx-python-api is required for HDX source. "
            "Install it with: pip install hdx-python-api"
        )

    try:
        Configuration.create(hdx_site="prod", user_agent="GeoAfrica-SDK")
    except Exception:
        pass  # Already configured

    query = f"cod-ab-{iso3.lower()}"
    datasets = Dataset.search_in_hdx(query, rows=1)
    if not datasets:
        raise DataNotFoundError(
            f"No HDX boundary dataset found for ISO '{iso3}'.",
            query=iso3,
        )

    dataset = datasets[0]
    resources = [
        r for r in dataset.get_resources()
        if r.get_file_type() in ("SHP", "GEOJSON", "GPKG", "ZIP")
    ]
    if not resources:
        raise DataNotFoundError(
            f"No downloadable boundary resources in HDX dataset for '{iso3}'.",
            query=iso3,
        )

    resource = resources[0]
    cfg = get_config()
    dest = cfg.cache_dir / "boundaries" / f"hdx_{iso3}_{level}"

    url, path = resource.download(folder=str(dest))
    path = Path(path)

    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as zf:
            zf.extractall(dest)
        shp_files = list(dest.glob("**/*.shp"))
        gpkg_files = list(dest.glob("**/*.gpkg"))
        geojson_files = list(dest.glob("**/*.geojson"))
        found = shp_files or gpkg_files or geojson_files
        if not found:
            raise DataNotFoundError(f"No geometry file found in HDX archive for '{iso3}'.")
        path = found[0]

    gdf = gpd.read_file(str(path))
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    return gdf.to_crs(crs)


def _iso2_region(iso2: str) -> str:
    _africa = {
        "DZ","AO","BJ","BW","BF","BI","CV","CM","CF","TD","KM","CG","CD","CI",
        "DJ","EG","GQ","ER","SZ","ET","GA","GM","GH","GN","GW","KE","LS","LR",
        "LY","MG","MW","ML","MR","MU","MA","MZ","NA","NE","NG","RW","ST","SN",
        "SL","SO","ZA","SS","SD","TZ","TG","TN","UG","ZM","ZW",
    }
    _americas = {"US", "CA", "BR", "MX"}
    _asia = {"IN", "CN", "JP", "PK", "BD", "ID"}
    _europe = {"GB", "FR", "DE"}

    if iso2 in _africa:
        return "Africa"
    if iso2 in _americas:
        return "Americas"
    if iso2 in _asia:
        return "Asia"
    if iso2 in _europe:
        return "Europe"
    return "Other"
