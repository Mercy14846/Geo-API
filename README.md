# GeoAfrica SDK

<div align="center">

![GeoAfrica Banner](https://img.shields.io/badge/GeoAfrica-SDK-4FC3F7?style=for-the-badge&logo=globe&logoColor=white)
![PyPI](https://img.shields.io/badge/PyPI-geoafrica-orange?style=for-the-badge&logo=pypi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Built by](https://img.shields.io/badge/Built%20by-Merczcord%20Technologies%20Ltd.-blueviolet?style=for-the-badge)

**One `pip install`. Every geospatial dataset. Any country on Earth.**

*Specialising in African communities, powered entirely by open data.*

</div>

---

## Overview

**GeoAfrica** is a unified Python SDK for geospatial data access, built and maintained by **Merczcord Technologies Ltd.**  
It aggregates **10+ authoritative open-data sources** into a single, developer-friendly interface, no complex API wrangling, no data format juggling.

Whether you're mapping health facilities in Nigeria, tracking active wildfires in Ethiopia, analysing population density in Kenya, or querying road networks across West Africa, one import is all you need.

```python
import geoafrica

# That's it. Every dataset in Africa and the world, at your fingertips.
```

---

## Features

| Module | What it does | Data Source |
|--------|-------------|-------------|
| `geoafrica.boundaries` | Admin boundaries at any level (0–3) | GADM, HDX |
| `geoafrica.population` | Population grids & statistics | WorldPop, SEDAC |
| `geoafrica.osm` | Any OSM feature — hospitals, roads, schools | OpenStreetMap / Overpass |
| `geoafrica.satellite` | Sentinel-2, Landsat, Digital Earth Africa STAC | DE Africa, Earth Search |
| `geoafrica.climate` | Rainfall & temperature rasters | CHIRPS, ERA5 |
| `geoafrica.health` | Health facilities worldwide | HealthSites.io, WHO |
| `geoafrica.fire` | Near real-time & historical fire detections | NASA FIRMS |
| `geoafrica.elevation` | DEM — SRTM, Copernicus, AW3D30, NASADEM | OpenTopography |
| `geoafrica.humanitarian` | Crisis, displacement, flood datasets | UN OCHA HDX |
| `geoafrica.roads` | Road networks & density stats | OpenStreetMap |
| `geoafrica.viz` | Interactive Folium maps, choropleths | — |
| `geoafrica.analysis` | Clip, buffer, zonal stats, proximity | — |

---

## Installation

```bash
pip install geoafrica
```

For satellite imagery support:
```bash
pip install geoafrica[satellite]
```

For climate ERA5 support:
```bash
pip install geoafrica[climate]
```

Full install (everything):
```bash
pip install geoafrica[full]
```

> **Python 3.9+ required.** Works on Windows, macOS, and Linux.

---

## API Keys

Most modules work **without any API key**. A few providers require a free registration:

| Provider | Required For | Register |
|----------|-------------|---------|
| NASA FIRMS | `geoafrica.fire` | [firms.modaps.eosdis.nasa.gov](https://firms.modaps.eosdis.nasa.gov/api/) |
| OpenTopography | `geoafrica.elevation` (large areas) | [portal.opentopography.org](https://portal.opentopography.org/requestApiKey) |
| Copernicus CDS | ERA5 climate data | [cds.climate.copernicus.eu](https://cds.climate.copernicus.eu/) |

Set your keys via CLI:
```bash
geoafrica config set GEOAFRICA_FIRMS_KEY your_key_here
```

Or via environment variables:
```bash
export GEOAFRICA_FIRMS_KEY=your_key_here
```

Or in Python:
```python
import geoafrica
geoafrica.configure(nasa_firms_key="your_key_here")
```

---

## Usage Examples

### Administrative Boundaries

```python
from geoafrica import boundaries

# Country outline
nigeria = boundaries.get_country("Nigeria")

# States / provinces
states = boundaries.get_admin("Nigeria", level=1)

# Districts
districts = boundaries.get_admin("Kenya", level=2)

# By ISO code
ghana = boundaries.get_by_iso("GH", level=1)

# Bounding box
bbox = boundaries.get_bbox("Ethiopia")  # [33.0, 3.4, 47.9, 14.9]

# List all supported countries
all_countries = boundaries.list_countries()
africa_only = boundaries.list_countries(region="Africa")
```

### Population Data

```python
from geoafrica import population

# 1km population grid (WorldPop)
pop_grid = population.get_grid("Nigeria", year=2020, resolution=1000)
print(f"Total pop: {int(pop_grid.where(pop_grid > 0).sum().values):,}")

# Admin-level statistics
stats = population.get_stats("Lagos", country="Nigeria", level=1)
# Returns DataFrame: admin_name, population, area_km2, density_per_km2

# Available data years
years = population.available_years("Ghana")
```

### OpenStreetMap Features

```python
from geoafrica import osm

# Hospitals in Lagos
hospitals = osm.get_amenity("Lagos, Nigeria", amenity="hospital")

# Schools across Ghana
schools = osm.get_amenity("Ghana", amenity="school")

# Primary roads in Nairobi
roads = osm.get_roads("Nairobi", road_type="primary")

# Buildings in a city
buildings = osm.get_buildings("Kigali")

# Custom tags — any OSM feature
water_sources = osm.get_features(
    "Ethiopia",
    tags={"amenity": "drinking_water"}
)

# Search within a bounding box
markets = osm.get_features_bbox(
    bbox=[3.0, 6.3, 3.5, 6.7],
    tags={"amenity": "marketplace"}
)
```

### Climate Data (CHIRPS Rainfall)

```python
from geoafrica import climate

# Annual rainfall for Ethiopia
rain_2023 = climate.get_rainfall("Ethiopia", year=2023)

# Monthly rainfall (July 2022)
rain_july = climate.get_rainfall("Nigeria", year=2022, month=7)

# Monthly time series as DataFrame
monthly = climate.monthly_series("Ghana", year=2023)
# month | month_name | mean_rainfall_mm | max_rainfall_mm

# Rainfall anomaly vs 1981–2010 baseline
anomaly = climate.rainfall_anomaly("Senegal", year=2022)
```

### Active Fires (NASA FIRMS)

```python
from geoafrica import fire

# Active fires in Nigeria (last 7 days)
fires = fire.get_country("Nigeria", days=7)

# Fires in West Africa bounding box
west_africa = fire.get_active(bbox=[-18, 4, 16, 20], days=3)

# Historical fire data
hist = fire.get_historical(
    "Democratic Republic of Congo",
    start="2023-01-01",
    end="2023-12-31"
)

# Quick summary
summary = fire.summary(fires, by="acq_date")
```

### Elevation & Terrain

```python
from geoafrica import elevation

# SRTM 30m DEM for Rwanda
dem = elevation.get_dem("Rwanda", source="SRTMGL1")

# Copernicus 30m DEM
dem_cop = elevation.get_dem("Kenya", source="COP30")

# Elevation profile between two points
profile = elevation.terrain_profile(
    start=(36.8, 3.8),   # (lon, lat) near Addis Ababa
    end=(38.7, 6.1),
    num_points=200,
)
profile.plot(x="distance_km", y="elevation_m")

# Slope and aspect
slope, aspect = elevation.compute_slope_aspect(dem)

# List all available DEM sources
elevation.list_sources()
```

### Health Facilities

```python
from geoafrica import health

# All hospitals in Nigeria
hospitals = health.get_facilities("Nigeria", facility_type="hospital")

# Clinics in Ghana
clinics = health.get_facilities("Ghana", facility_type="clinic")

# Nearest 3 hospitals to a point (e.g. Lagos Island)
nearest = health.nearest_to(lat=6.45, lon=3.39, country="Nigeria", n=3)

# Facility count per state
counts = health.count_by_admin("Kenya", level=1)
```

### Humanitarian Data (HDX)

```python
from geoafrica import humanitarian

# Search datasets
results = humanitarian.search("Nigeria flood 2024", rows=10)

# Get all resources in a dataset
resources = humanitarian.get_dataset("cod-ab-nga")

# Download shapefiles
files = humanitarian.download_dataset("cod-ab-nga", resource_format="SHP")

# Country-specific data
nigeria_data = humanitarian.get_country_datasets("Nigeria", data_type="displacement")

# Load as GeoDataFrame directly
gdf = humanitarian.load_geospatial("cod-ab-nga")
```

### Satellite Imagery

```python
from geoafrica import satellite

# Search Sentinel-2 scenes
items = satellite.search(
    collection="sentinel-2-l2a",
    country="Rwanda",
    date_range="2023-06-01/2023-09-30",
    max_cloud_cover=15,
    limit=5,
)
print(f"Found {len(items)} scenes")

# List all collections from Digital Earth Africa
deafrica_cols = satellite.deafrica_products()

# Load RGB composite
rgb = satellite.load_rgb(items[0])
```

### Analysis Tools

```python
from geoafrica.analysis import spatial, zonal_stats, proximity

# Clip hospitals to Lagos state
lagos = boundaries.get_admin("Lagos", country="Nigeria", level=1)
lagos_hospitals = spatial.clip(hospitals, lagos)

# Buffer schools by 2km (service area)
school_zones = spatial.buffer_km(schools, km=2)

# Population within admin units (zonal stats)
pop_stats = zonal_stats.compute(pop_grid, states, stats=["mean", "sum", "max"])

# Find nearest facility for each village
result = proximity.nearest_facility(villages, hospitals)

# Service coverage — % of population within 5km of any hospital
coverage = proximity.service_coverage(hospitals, pop_grid, radius_km=5)
print(f"Coverage: {coverage['coverage_pct']}%")
```

### Visualization

```python
from geoafrica import viz

# Quick interactive map
m = viz.quick_map(hospitals, color="#E91E63", tooltip_cols=["name", "facility_type"])
m.save("hospitals.html")

# Choropleth map
m = viz.choropleth(
    states.merge(pop_stats, on="NAME_1"),
    column="sum",
    title="Nigeria — Population by State",
)
m.save("population_choropleth.html")

# Multi-layer map
m = viz.quick_map(states)
viz.add_layer(m, hospitals, name="Hospitals", color="#E53935")
viz.add_layer(m, schools, name="Schools", color="#43A047")
m.save("multi_layer.html")

# Fire heatmap
fires_map = viz.fire_map(fires, country="Nigeria")
fires_map.save("fires.html")
```

### I/O

```python
from geoafrica.io import readers, writers

# Read any geospatial file
gdf = readers.read("data/nigeria.geojson")
gdf = readers.read("s3://my-bucket/data.gpkg", layer="roads")

# Read CSV with lat/lon columns
gdf = readers.read_csv_geo("hospitals.csv", lat_col="lat", lon_col="lng")

# Write to multiple formats
writers.to_geojson(hospitals, "hospitals.geojson")
writers.to_shapefile(hospitals, "hospitals.shp")
writers.to_geopackage(hospitals, "data.gpkg", layer="hospitals")
writers.to_csv(hospitals, "hospitals.csv")
writers.to_geoparquet(hospitals, "hospitals.parquet")
```

---

## CLI Usage

```bash
# Show version and API key status
geoafrica info

# Download boundaries
geoafrica boundaries nigeria --level 1 --output states.geojson
geoafrica boundaries ghana --level 2 --source hdx --output gh_districts.gpkg

# OpenStreetMap queries
geoafrica osm facilities --location "Kenya" --type hospital --output ke_hospitals.geojson
geoafrica osm roads --location "Lagos, Nigeria" --type primary

# Fire detections
geoafrica fire active --country Nigeria --days 7 --output fires.geojson
geoafrica fire active --bbox "-18,4,30,20" --days 3

# Elevation
geoafrica elevation dem --country Rwanda --source COP30 --output rwanda.tif
geoafrica elevation sources

# Configuration
geoafrica config set GEOAFRICA_FIRMS_KEY your_nasa_key
geoafrica config show

# List countries
geoafrica countries --region africa
```

---

## Supported Countries

GeoAfrica has built-in support for all **54 African nations** plus major countries worldwide.
Use any of the following identifier formats:

```python
# These all work
boundaries.get_country("Nigeria")
boundaries.get_country("NG")       # ISO-2
boundaries.get_country("NGA")      # ISO-3
boundaries.get_country("DRC")      # Common abbreviation
```

---

## Architecture

```
geoafrica/
├── core/          # Config, HTTP session, exceptions
├── datasets/      # 10 data modules (boundaries, population, osm, ...)
├── analysis/      # Spatial ops, zonal stats, proximity
├── io/            # Universal readers & writers
└── viz/           # Folium interactive maps
```

**Design principles:**
- **Plug-and-play** — zero config for most modules
- **Smart caching** — downloads cached locally to avoid re-fetching
- **Retry logic** — automatic retry with exponential backoff
- **Rate limiting** — per-host rate limiting to respect API policies
- **Standard outputs** — all vector data returns `GeoDataFrame`, rasters return `xarray.DataArray`

---

## Data Attribution

GeoAfrica aggregates open data. Please attribute the original providers:

| Source | License | Citation |
|--------|---------|---------|
| GADM | CC BY 4.0 (non-commercial) | gadm.org |
| WorldPop | CC BY 4.0 | worldpop.org |
| OpenStreetMap | ODbL | © OpenStreetMap contributors |
| NASA FIRMS | Open | NASA EOSDIS FIRMS |
| CHIRPS | Open | Funk et al., 2015 |
| HealthSites.io | CC BY 4.0 | healthsites.io |
| HDX / UN OCHA | CC BY-IGO 3.0 | data.humdata.org |
| OpenTopography | CC BY 4.0 | opentopography.org |

---

## Contributing

Contributions are welcome! To add a new data module:

1. Create `src/geoafrica/datasets/your_module.py`
2. Follow the existing module pattern (returns `GeoDataFrame` or `DataArray`)
3. Add unit tests in `tests/test_your_module.py`
4. Add to `src/geoafrica/datasets/__init__.py`
5. Submit a PR

---

## License

MIT License — see [LICENSE](LICENSE).

---

## About Merczcord Technologies Ltd.

**GeoAfrica** is a product of **Merczcord Technologies Ltd.**, a technology company focused on building data infrastructure and geospatial intelligence tools for African communities and beyond.

- Website: [merczcord.com](https://merczcord.com)
- Contact: info@merczcord.com
- GitHub: [github.com/Mercy14846/Geo-API](https://github.com/Mercy14846/Geo-API)

---

<div align="center">
  <sub>Made with ❤️ for Africa and the world by <b>Merczcord Technologies Ltd.</b></sub>
</div>