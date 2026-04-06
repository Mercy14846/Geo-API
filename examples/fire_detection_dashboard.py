#!/usr/bin/env python
"""
Example: Active Fire Detection Dashboard
==========================================
Built with GeoAfrica SDK by Merczcord Technologies Ltd.

This example demonstrates:
1. Fetching NASA FIRMS active fire data
2. Summarising detections by date
3. Generating a fire heatmap

Requirements: Set GEOAFRICA_FIRMS_KEY environment variable.
Register free at: https://firms.modaps.eosdis.nasa.gov/api/
"""

import os
from geoafrica import fire, viz, boundaries
from geoafrica.io import writers

print("=" * 60)
print("  GeoAfrica SDK — Fire Detection Dashboard")
print("  Merczcord Technologies Ltd.")
print("=" * 60)

if not os.environ.get("GEOAFRICA_FIRMS_KEY"):
    print("\n⚠  GEOAFRICA_FIRMS_KEY not set.")
    print("   Register at: https://firms.modaps.eosdis.nasa.gov/api/")
    print("   Then run: export GEOAFRICA_FIRMS_KEY=your_key")
    exit(0)

TARGET = "Nigeria"
DAYS = 7

print(f"\n[1/3] Fetching active fires in {TARGET} (last {DAYS} days)...")
fires = fire.get_country(TARGET, days=DAYS, sensor="VIIRS_SNPP")
print(f"      ✓ {len(fires)} fire detections")

if fires.empty:
    print("No fires detected. Try increasing --days or a different region.")
    exit(0)

print("\n[2/3] Summary by date:")
summary_df = fire.summary(fires, by="acq_date")
print(summary_df.to_string(index=False))

print("\n[3/3] Generating fire heatmap...")
m = viz.fire_map(fires, country=TARGET, title=f"{TARGET} Active Fires — Last {DAYS} Days")
m.save("fire_dashboard.html")
print("      ✓ Saved to fire_dashboard.html")

# Also export to CSV
writers.to_csv(fires, "fires.csv")
print(f"      ✓ Data exported to fires.csv")

print("\nDone! Open fire_dashboard.html in your browser.")
