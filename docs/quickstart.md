# Quick Start

## 1. Install

```bash
pip install geoafrica
```

## 2. Configure API Keys (optional)

Most modules require **no API key**. For fire data:

```bash
geoafrica config set GEOAFRICA_FIRMS_KEY your_nasa_firms_key
```

Register free at: https://firms.modaps.eosdis.nasa.gov/api/

## 3. Your First Map

```python
from geoafrica import boundaries, osm, health, viz

# Load Nigeria state boundaries
states = boundaries.get_admin("Nigeria", level=1)

# Find hospitals in Nigeria via OpenStreetMap
hospitals = osm.get_amenity("Nigeria", amenity="hospital")
print(f"Found {len(hospitals)} hospitals")

# Interactive map
m = viz.quick_map(states)
viz.add_layer(m, hospitals, name="Hospitals", color="red")
m.save("nigeria.html")
```

## 4. Population Analysis

```python
from geoafrica import population, boundaries
from geoafrica.analysis import zonal_stats

states = boundaries.get_admin("Kenya", level=1)
pop_grid = population.get_grid("Kenya", year=2020)

# Mean population per state
stats = zonal_stats.compute(pop_grid, states, stats=["sum", "mean", "max"])
print(stats.sort_values("sum", ascending=False).head())
```

## 5. Fire Detection

```python
from geoafrica import fire, viz

fires = fire.get_country("Nigeria", days=7)
print(f"{len(fires)} fire detections in the last 7 days")

m = viz.fire_map(fires, country="Nigeria")
m.save("fires.html")
```

## 6. Elevation Profile

```python
from geoafrica import elevation

profile = elevation.terrain_profile(
    start=(36.8, 3.8),
    end=(40.0, 9.0),
    num_points=100,
)
profile.plot(x="distance_km", y="elevation_m", title="Ethiopia Elevation Profile")
```

## 7. CLI Quick Reference

```bash
geoafrica info
geoafrica boundaries nigeria --level 1 --output states.geojson
geoafrica osm facilities --location "Nairobi" --type hospital
geoafrica fire active --country nigeria --days 7
geoafrica elevation dem --country rwanda --source COP30
geoafrica countries --region africa
```
