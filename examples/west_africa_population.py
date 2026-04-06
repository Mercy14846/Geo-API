#!/usr/bin/env python
"""
Example: Africa Population Density
=====================================
Built with GeoAfrica SDK by Merczcord Technologies Ltd.

This example demonstrates:
1. Fetching WorldPop population grids
2. Computing population stats per admin unit
3. Visualising a choropleth map
"""

from geoafrica import boundaries, population, viz
from geoafrica.analysis import zonal_stats

print("=" * 60)
print("  GeoAfrica SDK — Population Density Example")
print("  Merczcord Technologies Ltd.")
print("=" * 60)

COUNTRIES = ["Ghana", "Senegal", "Ivory Coast"]

for country in COUNTRIES:
    print(f"\n── {country} ──")
    try:
        states = boundaries.get_admin(country, level=1)
        pop_grid = population.get_grid(country, year=2020, resolution=1000)
        stats = zonal_stats.compute(pop_grid, states, stats=["sum", "mean"])
        print(f"   Top 3 most populous states:")
        top = stats.nlargest(3, "sum")[["zone", "sum", "mean"]]
        top.columns = ["Admin Unit", "Total Population", "Avg Pop/Cell"]
        print(top.to_string(index=False))
    except Exception as e:
        print(f"   Skipped: {e}")

print("\nDone!")
