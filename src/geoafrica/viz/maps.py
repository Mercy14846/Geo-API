"""
GeoAfrica — Visualization Module
===================================
Merczcord Technologies Ltd.

One-liner interactive maps powered by Folium/Leaflet.

Usage
-----
    from geoafrica import viz

    # Quick interactive map
    m = viz.quick_map(hospitals)
    m.save("hospitals.html")

    # Choropleth map
    m = viz.choropleth(states, column="population", title="Nigeria Population")

    # Multi-layer map
    m = viz.quick_map(states)
    viz.add_layer(m, hospitals, color="red", name="Hospitals")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import geopandas as gpd

if TYPE_CHECKING:
    import folium


def quick_map(
    gdf: gpd.GeoDataFrame,
    color: str = "#2196F3",
    opacity: float = 0.7,
    weight: float = 2,
    tooltip_cols: list[str] | None = None,
    zoom_start: int = 6,
    title: str | None = None,
) -> folium.Map:
    """
    Create an interactive Leaflet map from a GeoDataFrame.

    Parameters
    ----------
    gdf : GeoDataFrame
        Features to display.
    color : str
        Fill/line colour (CSS colour or hex). Default '#2196F3'.
    opacity : float
        Fill opacity (0–1). Default 0.7.
    weight : float
        Line weight for lines/polygons.
    tooltip_cols : list of str, optional
        Columns to show in tooltip. Auto-detects if None.
    zoom_start : int
        Initial zoom level.
    title : str, optional
        Map title shown in top-left corner.

    Returns
    -------
    folium.Map

    Examples
    --------
    >>> from geoafrica import boundaries, viz
    >>> ng = boundaries.get_admin("Nigeria", level=1)
    >>> m = viz.quick_map(ng, color="#FF5722", tooltip_cols=["NAME_1"])
    >>> m.save("nigeria_states.html")
    """
    try:
        import folium
    except ImportError:
        raise ImportError("Install folium: pip install folium")

    # Compute map centre
    bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
    centre_lat = (bounds[1] + bounds[3]) / 2
    centre_lon = (bounds[0] + bounds[2]) / 2

    m = folium.Map(
        location=[centre_lat, centre_lon],
        zoom_start=zoom_start,
        tiles="CartoDB Positron",
        control_scale=True,
    )

    # Add Merczcord branding
    _add_branding(m, title=title)

    # Tooltip columns
    if tooltip_cols is None:
        tooltip_cols = [
            c for c in gdf.columns
            if c != "geometry" and gdf[c].dtype == object
        ][:4]

    # Determine style based on geometry type
    geom_type = gdf.geometry.geom_type.iloc[0] if not gdf.empty else "Point"

    if "Point" in geom_type:
        for _, row in gdf.iterrows():
            if row.geometry is None:
                continue
            tooltip_text = "<br>".join(
                f"<b>{c}:</b> {row.get(c, '')}" for c in tooltip_cols
            )
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=5,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=opacity,
                tooltip=folium.Tooltip(tooltip_text),
            ).add_to(m)
    else:
        gdf_wgs = gdf.to_crs("EPSG:4326") if gdf.crs != "EPSG:4326" else gdf
        tooltip = (
            folium.GeoJsonTooltip(fields=tooltip_cols, aliases=tooltip_cols)
            if tooltip_cols else None
        )

        folium.GeoJson(
            gdf_wgs.__geo_interface__,
            style_function=lambda _: {
                "color": color,
                "weight": weight,
                "fillColor": color,
                "fillOpacity": opacity,
            },
            tooltip=tooltip,
        ).add_to(m)

    # Fit bounds
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
    return m


def choropleth(
    gdf: gpd.GeoDataFrame,
    column: str,
    title: str | None = None,
    cmap: str = "YlOrRd",
    bins: int = 7,
    tooltip_cols: list[str] | None = None,
    legend_name: str | None = None,
) -> folium.Map:
    """
    Create a choropleth map colouring polygons by a numeric column.

    Parameters
    ----------
    gdf : GeoDataFrame
        Polygon features.
    column : str
        Numeric column to visualise.
    title : str, optional
        Map title.
    cmap : str
        Matplotlib/Brewer colormap name. Default 'YlOrRd'.
    bins : int
        Number of colour bins.
    tooltip_cols : list of str, optional
        Columns to show in tooltip.
    legend_name : str, optional
        Legend label.

    Returns
    -------
    folium.Map

    Examples
    --------
    >>> stats = population.get_stats(...)
    >>> m = viz.choropleth(states.merge(stats), column="population")
    """
    try:
        import branca.colormap as cm
        import folium
    except ImportError:
        raise ImportError("Install folium and branca: pip install folium")

    gdf_wgs = gdf.to_crs("EPSG:4326") if gdf.crs != "EPSG:4326" else gdf

    if column not in gdf_wgs.columns:
        raise ValueError(f"Column '{column}' not found. Available: {list(gdf.columns)}")

    values = gdf_wgs[column].dropna()
    if values.empty:
        raise ValueError(f"Column '{column}' has no valid data.")

    bounds = gdf_wgs.total_bounds
    centre_lat = (bounds[1] + bounds[3]) / 2
    centre_lon = (bounds[0] + bounds[2]) / 2

    m = folium.Map(
        location=[centre_lat, centre_lon],
        zoom_start=5,
        tiles="CartoDB Positron",
        control_scale=True,
    )
    _add_branding(m, title=title or f"Choropleth: {column}")

    # Build colormap
    colormap = cm.linear.__dict__.get(
        cmap.replace(".", "_"),
        cm.linear.YlOrRd_09,
    ).scale(values.min(), values.max())
    colormap.caption = legend_name or column
    colormap.add_to(m)

    if tooltip_cols is None:
        tooltip_cols = [c for c in gdf.columns if c != "geometry"][:5]

    folium.GeoJson(
        gdf_wgs.__geo_interface__,
        style_function=lambda feature: {
            "fillColor": colormap(feature["properties"].get(column, 0) or 0),
            "color": "#444444",
            "weight": 0.5,
            "fillOpacity": 0.75,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=tooltip_cols,
            aliases=tooltip_cols,
        ),
    ).add_to(m)

    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
    return m


def add_layer(
    m: folium.Map,
    gdf: gpd.GeoDataFrame,
    name: str = "Layer",
    color: str = "#E91E63",
    opacity: float = 0.7,
    tooltip_cols: list[str] | None = None,
) -> folium.Map:
    """
    Add an additional GeoDataFrame layer to an existing Folium map.

    Parameters
    ----------
    m : folium.Map
        Existing map.
    gdf : GeoDataFrame
        Features to add.
    name : str
        Layer name in the layer control.
    color, opacity : style params.
    tooltip_cols : list of str, optional

    Returns
    -------
    folium.Map (modified in-place)
    """
    try:
        import folium
    except ImportError:
        raise ImportError("Install folium: pip install folium")

    gdf_wgs = gdf.to_crs("EPSG:4326") if gdf.crs != "EPSG:4326" else gdf
    geom_type = gdf_wgs.geometry.geom_type.iloc[0] if not gdf_wgs.empty else "Point"

    if tooltip_cols is None:
        tooltip_cols = [c for c in gdf_wgs.columns if c != "geometry"][:4]

    fg = folium.FeatureGroup(name=name)

    if "Point" in geom_type:
        for _, row in gdf_wgs.iterrows():
            if row.geometry is None:
                continue
            tooltip_text = "<br>".join(
                f"<b>{c}:</b> {row.get(c, '')}" for c in tooltip_cols
            )
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=5,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=opacity,
                tooltip=folium.Tooltip(tooltip_text),
            ).add_to(fg)
    else:
        tooltip = folium.GeoJsonTooltip(fields=tooltip_cols) if tooltip_cols else None
        folium.GeoJson(
            gdf_wgs.__geo_interface__,
            name=name,
            style_function=lambda _: {
                "color": color,
                "weight": 1.5,
                "fillColor": color,
                "fillOpacity": opacity,
            },
            tooltip=tooltip,
        ).add_to(fg)

    fg.add_to(m)
    folium.LayerControl().add_to(m)
    return m


def fire_map(
    fire_gdf: gpd.GeoDataFrame,
    country: str | None = None,
    title: str = "Active Fire Detections",
) -> folium.Map:
    """
    Specialised fire detection map with heat-map style rendering.

    Parameters
    ----------
    fire_gdf : GeoDataFrame
        Output from fire.get_active() or fire.get_country().
    country : str, optional
        Country to overlay as boundary.
    title : str
        Map title.

    Returns
    -------
    folium.Map
    """
    try:
        import folium
        from folium.plugins import HeatMap
    except ImportError:
        raise ImportError("Install folium: pip install folium")

    gdf = fire_gdf.to_crs("EPSG:4326")
    heat_data = [[row.geometry.y, row.geometry.x] for _, row in gdf.iterrows() if row.geometry]

    bounds = gdf.total_bounds
    m = folium.Map(
        location=[(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2],
        zoom_start=5,
        tiles="CartoDB Dark_Matter",
    )
    _add_branding(m, title=title)
    HeatMap(heat_data, radius=10, blur=12, max_zoom=13).add_to(m)

    if country:
        from geoafrica.datasets.boundaries import get_country
        boundary = get_country(country)
        folium.GeoJson(
            boundary.__geo_interface__,
            style_function=lambda _: {"color": "#FFFFFF", "weight": 1.5, "fillOpacity": 0},
        ).add_to(m)

    return m


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _add_branding(m: folium.Map, title: str | None = None) -> None:
    """Add a Merczcord Technologies branding panel to the map."""
    try:
        import folium
        brand_html = """
        <div style="
            position: fixed;
            bottom: 20px; left: 20px; z-index: 9999;
            background: rgba(0,0,0,0.75);
            color: white;
            padding: 8px 14px;
            border-radius: 8px;
            font-family: 'Inter', sans-serif;
            font-size: 12px;
            backdrop-filter: blur(6px);
            border: 1px solid rgba(255,255,255,0.1);
        ">
            <b style="color:#4FC3F7;">GeoAfrica SDK</b><br>
            <span style="opacity:0.7;font-size:10px;">Merczcord Technologies Ltd.</span>
        </div>
        """
        if title:
            title_html = f"""
            <div style="
                position: fixed;
                top: 20px; left: 50%; transform: translateX(-50%);
                z-index: 9999;
                background: rgba(0,0,0,0.8);
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                font-family: 'Inter', sans-serif;
                font-size: 15px;
                font-weight: 600;
                backdrop-filter: blur(6px);
            ">{title}</div>
            """
            m.get_root().html.add_child(folium.Element(title_html))
        m.get_root().html.add_child(folium.Element(brand_html))
    except Exception:
        pass
