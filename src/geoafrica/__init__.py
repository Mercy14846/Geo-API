"""
GeoAfrica — Unified Geospatial Data SDK
=========================================
Built by Merczcord Technologies Ltd.

One pip install. Every dataset. Anywhere on Earth.

Quick Start
-----------
    import geoafrica

    # Administrative boundaries
    from geoafrica import boundaries
    nigeria = boundaries.get_country("Nigeria")
    states  = boundaries.get_admin("Nigeria", level=1)

    # OpenStreetMap features
    from geoafrica import osm
    hospitals = osm.get_amenity("Lagos, Nigeria", amenity="hospital")

    # Population grids
    from geoafrica import population
    pop = population.get_grid("Kenya", year=2020)

    # Rainfall (CHIRPS)
    from geoafrica import climate
    rain = climate.get_rainfall("Ethiopia", year=2023, month=7)

    # Active fires (NASA FIRMS)
    from geoafrica import fire
    fires = fire.get_country("Nigeria", days=7)

    # Elevation (DEM)
    from geoafrica import elevation
    dem = elevation.get_dem("Rwanda", source="COP30")

    # Health facilities
    from geoafrica import health
    clinics = health.get_facilities("Ghana", facility_type="clinic")

    # Humanitarian/HDX data
    from geoafrica import humanitarian
    results = humanitarian.search("Nigeria flood 2024")

    # Visualization
    from geoafrica import viz
    m = viz.quick_map(hospitals)
    m.save("map.html")

    # Global configuration
    geoafrica.configure(verbose=True, cache_ttl=3600)
    geoafrica.configure(nasa_firms_key="YOUR_KEY_HERE")
"""

__version__ = "0.1.0"
__author__ = "Merczcord Technologies Ltd."
__email__ = "dev@merczcord.com"
__license__ = "MIT"
__url__ = "https://github.com/Mercy14846/Geo-API"

# ---------------------------------------------------------------------------
# Lazy module imports — keeps cold start fast
# ---------------------------------------------------------------------------

from geoafrica.core.config import get_config, configure  # noqa: F401
from geoafrica.core.exceptions import (               # noqa: F401
    GeoAfricaError,
    DataNotFoundError,
    APIKeyMissingError,
    RateLimitError,
    InvalidBoundingBoxError,
    UnsupportedFormatError,
)


def __getattr__(name: str):
    """Lazy-load submodules on first access."""
    _lazy_modules = {
        "boundaries":   "geoafrica.datasets.boundaries",
        "population":   "geoafrica.datasets.population",
        "osm":          "geoafrica.datasets.osm",
        "satellite":    "geoafrica.datasets.satellite",
        "climate":      "geoafrica.datasets.climate",
        "health":       "geoafrica.datasets.health",
        "fire":         "geoafrica.datasets.fire",
        "elevation":    "geoafrica.datasets.elevation",
        "humanitarian": "geoafrica.datasets.humanitarian",
        "roads":        "geoafrica.datasets.roads",
        "viz":          "geoafrica.viz.maps",
        "spatial":      "geoafrica.analysis.spatial",
        "zonal_stats":  "geoafrica.analysis.zonal_stats",
        "proximity":    "geoafrica.analysis.proximity",
        "readers":      "geoafrica.io.readers",
        "writers":      "geoafrica.io.writers",
    }
    if name in _lazy_modules:
        import importlib
        mod = importlib.import_module(_lazy_modules[name])
        globals()[name] = mod
        return mod
    raise AttributeError(f"module 'geoafrica' has no attribute '{name}'")


__all__ = [
    # Core
    "get_config",
    "configure",
    # Exceptions
    "GeoAfricaError",
    "DataNotFoundError",
    "APIKeyMissingError",
    "RateLimitError",
    "InvalidBoundingBoxError",
    "UnsupportedFormatError",
    # Dataset modules (lazy)
    "boundaries",
    "population",
    "osm",
    "satellite",
    "climate",
    "health",
    "fire",
    "elevation",
    "humanitarian",
    "roads",
    # Analysis
    "spatial",
    "zonal_stats",
    "proximity",
    # I/O
    "readers",
    "writers",
    # Visualization
    "viz",
]
