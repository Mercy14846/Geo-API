"""
GeoAfrica CLI
===============
Merczcord Technologies Ltd.

Command line interface for GeoAfrica SDK.

Usage
-----
    geoafrica --help
    geoafrica info
    geoafrica config set GEOAFRICA_FIRMS_KEY <key>
    geoafrica boundaries nigeria --level 1 --output states.geojson
    geoafrica osm facilities --location "Lagos, Nigeria" --type hospital
    geoafrica fire active --bbox "-18,4,30,20" --days 7
    geoafrica elevation dem --country Rwanda --source COP30
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()

BANNER = """
[bold cyan]  ██████╗ ███████╗ ██████╗  █████╗ ███████╗██████╗ ██╗ ██████╗ █████╗ [/bold cyan]
[bold cyan] ██╔════╝ ██╔════╝██╔═══██╗██╔══██╗██╔════╝██╔══██╗██║██╔════╝██╔══██╗[/bold cyan]
[bold cyan] ██║  ███╗█████╗  ██║   ██║███████║█████╗  ██████╔╝██║██║     ███████║[/bold cyan]
[bold cyan] ██║   ██║██╔══╝  ██║   ██║██╔══██║██╔══╝  ██╔══██╗██║██║     ██╔══██║[/bold cyan]
[bold cyan] ╚██████╔╝███████╗╚██████╔╝██║  ██║██║     ██║  ██║██║╚██████╗██║  ██║[/bold cyan]
[bold cyan]  ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝╚═╝ ╚═════╝╚═╝  ╚═╝[/bold cyan]
[dim]  Geospatial Data SDK — Built by Merczcord Technologies Ltd.[/dim]
"""


@click.group()
@click.version_option("0.2.0", prog_name="geoafrica")
def main():
    """GeoAfrica: Unified geospatial data SDK for Africa and the world."""
    pass


# ──────────────────────────────────────────────────────────────────────────────
# geoafrica info
# ──────────────────────────────────────────────────────────────────────────────
@main.command()
def info():
    """Show GeoAfrica SDK version, config, and API key status."""
    console.print(BANNER)
    from geoafrica.core.config import get_config
    cfg = get_config()
    cfg_info = cfg.info()

    table = Table(title="Configuration", show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    table.add_row("Cache directory", cfg_info["cache_dir"])
    table.add_row("Cache TTL", f"{cfg_info['cache_ttl_seconds']} seconds")
    table.add_row("HTTP timeout", f"{cfg_info['timeout_seconds']} seconds")
    table.add_row("Verbose mode", str(cfg_info["verbose"]))

    console.print(table)

    key_table = Table(title="API Keys", show_header=True, header_style="bold magenta")
    key_table.add_column("Provider", style="cyan")
    key_table.add_column("Status")
    key_table.add_column("Env Variable", style="dim")

    from geoafrica.core.config import ENV_KEYS
    for provider, env_var in ENV_KEYS.items():
        status = cfg_info["api_keys"].get(provider, "✗ not set")
        color = "green" if "✓" in status else "red"
        key_table.add_row(provider, f"[{color}]{status}[/{color}]", env_var)

    console.print(key_table)


# ──────────────────────────────────────────────────────────────────────────────
# geoafrica config
# ──────────────────────────────────────────────────────────────────────────────
@main.group()
def config():
    """Manage GeoAfrica configuration and API keys."""
    pass


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str):
    """Set an API key or config value. Example: geoafrica config set GEOAFRICA_FIRMS_KEY abc123"""
    from geoafrica.core.config import ENV_KEYS, get_config
    cfg = get_config()

    # Find provider by env var name or partial match
    provider = next(
        (p for p, env in ENV_KEYS.items() if env.upper() == key.upper() or p.upper() == key.upper()),
        key.upper(),
    )
    cfg.set_api_key(provider, value, persist=True)
    console.print(f"[green]✓[/green] API key for [cyan]{provider}[/cyan] saved.")


@config.command("show")
def config_show():
    """Show current configuration file path and contents."""
    from geoafrica.core.config import _CONFIG_FILE
    console.print(f"Config file: [cyan]{_CONFIG_FILE}[/cyan]")
    if _CONFIG_FILE.exists():
        console.print(_CONFIG_FILE.read_text())
    else:
        console.print("[dim]No config file found yet.[/dim]")


# ──────────────────────────────────────────────────────────────────────────────
# geoafrica boundaries
# ──────────────────────────────────────────────────────────────────────────────
@main.command()
@click.argument("country")
@click.option("--level", "-l", default=1, type=int, show_default=True, help="Admin level (0–3)")
@click.option("--output", "-o", default=None, help="Output file path (.geojson, .gpkg, .shp, .csv)")
@click.option("--source", default="gadm", show_default=True, help="Data source: gadm or hdx")
def boundaries(country: str, level: int, output: str | None, source: str):
    """Download administrative boundaries for a country.

    Example: geoafrica boundaries nigeria --level 1 --output states.geojson
    """
    from geoafrica.datasets.boundaries import get_admin
    with console.status(f"[cyan]Fetching {country} level-{level} boundaries from {source}...[/cyan]"):
        gdf = get_admin(country, level=level, source=source)

    console.print(f"[green]✓[/green] Retrieved [bold]{len(gdf)}[/bold] features.")
    _print_gdf_preview(gdf)
    _save_output(gdf, output, default_name=f"{country}_admin{level}.geojson")


# ──────────────────────────────────────────────────────────────────────────────
# geoafrica osm
# ──────────────────────────────────────────────────────────────────────────────
@main.group()
def osm():
    """Query OpenStreetMap features."""
    pass


@osm.command("facilities")
@click.option("--location", "-l", required=True, help="Location name (e.g. 'Lagos, Nigeria')")
@click.option("--type", "ftype", default="hospital", show_default=True,
              help="Facility type: hospital, school, clinic, bank, market, etc.")
@click.option("--output", "-o", default=None)
def osm_facilities(location: str, ftype: str, output: str | None):
    """Fetch facilities from OpenStreetMap.

    Example: geoafrica osm facilities --location "Kenya" --type hospital
    """
    from geoafrica.datasets.osm import get_amenity
    with console.status(f"[cyan]Querying {ftype}s in {location}...[/cyan]"):
        gdf = get_amenity(location, amenity=ftype)
    console.print(f"[green]✓[/green] Found [bold]{len(gdf)}[/bold] {ftype}(s).")
    _print_gdf_preview(gdf)
    _save_output(gdf, output, default_name=f"{ftype}_{location.replace(', ','_')}.geojson")


@osm.command("roads")
@click.option("--location", "-l", required=True)
@click.option("--type", "road_type", default=None, help="Road type: primary, secondary, etc.")
@click.option("--output", "-o", default=None)
def osm_roads(location: str, road_type: str | None, output: str | None):
    """Fetch road network from OpenStreetMap."""
    from geoafrica.datasets.osm import get_roads
    with console.status(f"[cyan]Fetching roads in {location}...[/cyan]"):
        gdf = get_roads(location, road_type=road_type)
    console.print(f"[green]✓[/green] Found [bold]{len(gdf)}[/bold] road segments.")
    _save_output(gdf, output, default_name=f"roads_{location.replace(', ','_')}.geojson")


# ──────────────────────────────────────────────────────────────────────────────
# geoafrica fire
# ──────────────────────────────────────────────────────────────────────────────
@main.group()
def fire():
    """NASA FIRMS active fire data commands."""
    pass


@fire.command("active")
@click.option("--country", "-c", default=None, help="Country name or ISO code.")
@click.option("--bbox", "-b", default=None,
              help="Bounding box: 'min_lon,min_lat,max_lon,max_lat'")
@click.option("--days", "-d", default=7, show_default=True, type=int)
@click.option("--sensor", default="VIIRS_SNPP", show_default=True)
@click.option("--output", "-o", default=None)
def fire_active(country: str | None, bbox: str | None, days: int, sensor: str, output: str | None):
    """Fetch near real-time active fire detections.

    Example: geoafrica fire active --country Nigeria --days 3
    """
    from geoafrica.datasets import fire as fire_mod
    if country:
        with console.status(f"[cyan]Fetching fires in {country} (last {days} days)...[/cyan]"):
            gdf = fire_mod.get_country(country, days=days, sensor=sensor)
    elif bbox:
        b = [float(x) for x in bbox.split(",")]
        with console.status(f"[cyan]Fetching fires for bbox (last {days} days)...[/cyan]"):
            gdf = fire_mod.get_active(bbox=b, days=days, sensor=sensor)
    else:
        console.print("[red]Provide --country or --bbox[/red]")
        sys.exit(1)

    console.print(f"[green]✓[/green] [bold]{len(gdf)}[/bold] fire detections.")
    _print_gdf_preview(gdf)
    name = f"fires_{country or 'bbox'}_{days}d.geojson"
    _save_output(gdf, output, default_name=name)


# ──────────────────────────────────────────────────────────────────────────────
# geoafrica elevation
# ──────────────────────────────────────────────────────────────────────────────
@main.group()
def elevation():
    """Digital Elevation Model (DEM) commands."""
    pass


@elevation.command("dem")
@click.option("--country", "-c", required=True)
@click.option("--source", "-s", default="SRTMGL1", show_default=True,
              help="DEM source: SRTMGL1, COP30, AW3D30, NASADEM")
@click.option("--output", "-o", default=None, help="Output .tif file path")
def elevation_dem(country: str, source: str, output: str | None):
    """Download a DEM for a country.

    Example: geoafrica elevation dem --country Rwanda --source COP30
    """
    from geoafrica.datasets.elevation import get_dem
    with console.status(f"[cyan]Downloading {source} DEM for {country}...[/cyan]"):
        da = get_dem(country, source=source)
    console.print(f"[green]✓[/green] Shape: {da.shape}, CRS: {da.rio.crs}")
    if output:
        da.rio.to_raster(output)
        console.print(f"Saved to [cyan]{output}[/cyan]")


@elevation.command("sources")
def elevation_sources():
    """List available DEM data sources."""
    from geoafrica.datasets.elevation import list_sources
    df = list_sources()
    table = Table(title="Available DEM Sources")
    table.add_column("Code", style="cyan")
    table.add_column("Description")
    for _, row in df.iterrows():
        table.add_row(row["code"], row["description"])
    console.print(table)


# ──────────────────────────────────────────────────────────────────────────────
# geoafrica countries
# ──────────────────────────────────────────────────────────────────────────────
@main.command()
@click.option("--region", "-r", default=None,
              help="Filter by region: africa, americas, asia, europe")
def countries(region: str | None):
    """List supported countries."""
    from geoafrica.datasets.boundaries import list_countries
    df = list_countries(region=region)
    table = Table(title=f"Supported Countries{f' ({region.title()})' if region else ''}")
    table.add_column("Country", style="cyan")
    table.add_column("ISO-2")
    table.add_column("ISO-3")
    table.add_column("Region")
    for _, row in df.iterrows():
        table.add_row(row["country"], row["iso2"], row["iso3"], row["region"])
    console.print(table)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _print_gdf_preview(gdf, n: int = 5):
    """Print a rich table preview of a GeoDataFrame."""
    cols = [c for c in gdf.columns if c != "geometry"][:6]
    if not cols:
        return
    table = Table(title=f"Preview ({min(n, len(gdf))} of {len(gdf)} rows)")
    for col in cols:
        table.add_column(col, style="dim", max_width=30)
    for _, row in gdf.head(n).iterrows():
        table.add_row(*[str(row.get(c, ""))[:30] for c in cols])
    console.print(table)


def _save_output(gdf, output: str | None, default_name: str):
    """Save GeoDataFrame to file based on extension."""
    from geoafrica.io.writers import to_csv, to_geojson, to_geopackage, to_shapefile
    if output is None:
        console.print("[dim]No output file specified. Use --output to save.[/dim]")
        return
    ext = Path(output).suffix.lower()
    if ext == ".geojson" or ext == ".json":
        to_geojson(gdf, output)
    elif ext == ".shp":
        to_shapefile(gdf, output)
    elif ext == ".gpkg":
        to_geopackage(gdf, output)
    elif ext == ".csv":
        to_csv(gdf, output)
    else:
        to_geojson(gdf, output + ".geojson")
        output = output + ".geojson"
    console.print(f"[green]✓[/green] Saved to [cyan]{output}[/cyan]")


if __name__ == "__main__":
    main()
