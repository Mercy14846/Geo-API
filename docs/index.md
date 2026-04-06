# GeoAfrica SDK

**Built by Merczcord Technologies Ltd.**

> *One `pip install`. Every geospatial dataset. Any country on Earth.*

GeoAfrica is a unified Python SDK providing seamless access to **10+ authoritative open-data sources** — tailored for African communities, usable worldwide.

## Installation

```bash
pip install geoafrica
```

## Quick Example

```python
from geoafrica import boundaries, osm, viz

# Get Nigeria's state boundaries
states = boundaries.get_admin("Nigeria", level=1)

# Find all hospitals in Lagos
hospitals = osm.get_amenity("Lagos, Nigeria", amenity="hospital")

# Render an interactive map
m = viz.quick_map(hospitals, tooltip_cols=["name"])
m.save("lagos_hospitals.html")
```

## Key Modules

| Module | Description |
|--------|-------------|
| `boundaries` | Admin boundaries from GADM & HDX |
| `population` | WorldPop population grids |
| `osm` | OpenStreetMap via Overpass API |
| `climate` | CHIRPS rainfall & temperature |
| `fire` | NASA FIRMS fire detections |
| `elevation` | SRTM, Copernicus DEM |
| `health` | Health facilities (HealthSites.io) |
| `humanitarian` | UN OCHA HDX crisis datasets |
| `satellite` | Sentinel-2, Landsat (STAC) |
| `roads` | OSM road networks |

## About

Merczcord Technologies Ltd. builds data infrastructure and geospatial intelligence tools for African communities.

- 🌐 [merczcord.com](https://merczcord.com)
- 📧 dev@merczcord.com
- 🐙 [GitHub](https://github.com/Mercy14846/Geo-API)
