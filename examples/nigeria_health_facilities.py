#!/usr/bin/env python
"""
Example: Nigeria Health Facility Analysis
==========================================
Built with GeoAfrica SDK by Merczcord Technologies Ltd.

This example demonstrates:
1. Fetching health facilities via OpenStreetMap
2. Overlaying with state boundaries
3. Counting facilities per state
4. Creating an interactive choropleth map
"""

from geoafrica import boundaries, osm, viz
from geoafrica.analysis import proximity

print("=" * 60)
print("  GeoAfrica SDK — Nigeria Health Facility Example")
print("  Merczcord Technologies Ltd.")
print("=" * 60)

# ── Step 1: Load state boundaries ────────────────────────────────────────────
print("\n[1/4] Loading Nigeria state boundaries...")
states = boundaries.get_admin("Nigeria", level=1)
print(f"      ✓ {len(states)} states loaded")

# ── Step 2: Fetch hospitals from OpenStreetMap ────────────────────────────────
print("\n[2/4] Fetching hospitals from OpenStreetMap...")
hospitals = osm.get_amenity("Nigeria", amenity="hospital")
print(f"      ✓ {len(hospitals)} hospitals found")

# ── Step 3: Count hospitals per state ────────────────────────────────────────
print("\n[3/4] Counting hospitals per state...")
import geopandas as gpd
joined = gpd.sjoin(hospitals, states[["NAME_1", "geometry"]], how="left", predicate="within")
counts = joined.groupby("NAME_1").size().reset_index(name="hospital_count")
print(counts.sort_values("hospital_count", ascending=False).head(10).to_string(index=False))

# ── Step 4: Create interactive map ───────────────────────────────────────────
print("\n[4/4] Generating interactive map...")
m = viz.quick_map(states, color="#1976D2", opacity=0.15, tooltip_cols=["NAME_1"])
viz.add_layer(m, hospitals, name="Hospitals", color="#E53935")
m.save("nigeria_hospitals.html")
print("      ✓ Map saved to nigeria_hospitals.html")

print("\nDone! Open nigeria_hospitals.html in your browser.")
