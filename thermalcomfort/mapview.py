"""Geographic map visualisation using folium (interactive HTML) and
matplotlib (static).

Main entry point: build_map() — creates an interactive folium map showing
UTCI stress categories at a specific datetime for a list of locations.
"""

from __future__ import annotations

import webbrowser
from pathlib import Path
from typing import Optional, Sequence

import folium
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .comfort.indices import UTCI_CATEGORIES, UTCI_COLORS


# ── Folium colour helpers ─────────────────────────────────────────────────────

def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _utci_color(value: float) -> str:
    for cat, (lo, hi) in UTCI_CATEGORIES.items():
        if lo <= value < hi:
            return UTCI_COLORS[cat]
    return "#aaaaaa"


def _utci_category_label(value: float) -> str:
    for cat, (lo, hi) in UTCI_CATEGORIES.items():
        if lo <= value < hi:
            return cat
    return "n/a"


# ── Interactive HTML map ──────────────────────────────────────────────────────

def build_map(
    data: dict[str, pd.DataFrame],
    dt: pd.Timestamp,
    variable: str = "utci",
    output_path: Optional[Path] = None,
    open_browser: bool = True,
) -> Path:
    """Build an interactive folium map for a given timestamp.

    Parameters
    ----------
    data : dict mapping location-name → DataFrame (output of calculate_comfort)
        Each DataFrame must have a UTC DatetimeIndex.
    dt : pd.Timestamp
        UTC timestamp to extract from each DataFrame (nearest hour).
    variable : str
        Column to visualise ('utci', 'temperature_2m', 'heat_index', etc.).
    output_path : Path, optional
        Where to save the HTML file. Defaults to /tmp/thermalcomfort_map.html.
    open_browser : bool
        Open the file in the default browser after saving.

    Returns
    -------
    Path to the saved HTML file.
    """
    if output_path is None:
        output_path = Path("/tmp/thermalcomfort_map.html")

    dt = _to_utc_hour(dt)

    # Compute centre
    all_lats, all_lons = [], []
    rows = []
    for name, df in data.items():
        # Extract lat/lon from df attrs if stored, else from marker metadata
        lat = df.attrs.get("lat")
        lon = df.attrs.get("lon")
        if lat is None or lon is None:
            continue

        # Find nearest hour
        idx = df.index.get_indexer([dt], method="nearest")[0]
        row = df.iloc[idx]
        val = row.get(variable, np.nan)

        rows.append({"name": name, "lat": lat, "lon": lon, "value": val, "row": row})
        all_lats.append(lat)
        all_lons.append(lon)

    if not rows:
        raise ValueError("No location data with lat/lon attributes. "
                         "Use build_map_from_locations() instead.")

    center_lat = np.mean(all_lats)
    center_lon = np.mean(all_lons)

    m = folium.Map(location=[center_lat, center_lon], zoom_start=6,
                   tiles="CartoDB positron")

    _add_utci_legend(m)

    for r in rows:
        color = _utci_color(r["value"]) if variable == "utci" else "#2196F3"
        cat = _utci_category_label(r["value"]) if variable == "utci" else ""
        popup_html = _build_popup(r["name"], r["row"], r["value"], variable, cat)

        folium.CircleMarker(
            location=[r["lat"], r["lon"]],
            radius=14,
            color="white",
            weight=1.5,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=260),
            tooltip=f"{r['name']}: {r['value']:.1f}°C",
        ).add_to(m)

        folium.map.Marker(
            location=[r["lat"], r["lon"]],
            icon=folium.DivIcon(
                html=f'<div style="font-size:9px;font-weight:bold;color:white;'
                     f'text-shadow:0 0 3px #000;white-space:nowrap;margin-top:-6px;'
                     f'margin-left:16px">{r["name"]}</div>',
                icon_size=(120, 20),
            ),
        ).add_to(m)

    # Title
    dt_local = dt.strftime("%Y-%m-%d %H:%M UTC")
    title_html = (
        f'<div style="position:fixed;top:10px;left:50%;transform:translateX(-50%);'
        f'background:rgba(255,255,255,0.9);padding:6px 14px;border-radius:6px;'
        f'font-size:14px;font-weight:bold;z-index:1000;box-shadow:0 2px 6px rgba(0,0,0,0.3)">'
        f'Thermal Comfort Map — {dt_local}</div>'
    )
    m.get_root().html.add_child(folium.Element(title_html))

    m.save(str(output_path))

    if open_browser:
        webbrowser.open(f"file://{output_path}")

    return output_path


def build_map_from_locations(
    locations_dfs: Sequence[tuple],
    dt: pd.Timestamp,
    variable: str = "utci",
    output_path: Optional[Path] = None,
    open_browser: bool = True,
) -> Path:
    """Convenience wrapper that accepts (LocationInfo, DataFrame) tuples.

    Parameters
    ----------
    locations_dfs : list of (LocationInfo, DataFrame)
    dt : pd.Timestamp  UTC timestamp
    """
    data = {}
    for loc, df in locations_dfs:
        df = df.copy()
        df.attrs["lat"] = loc.lat
        df.attrs["lon"] = loc.lon
        data[str(loc)] = df
    return build_map(data, dt, variable=variable, output_path=output_path,
                     open_browser=open_browser)


# ── Static matplotlib map ─────────────────────────────────────────────────────

def plot_map_static(
    locations_dfs: Sequence[tuple],
    dt: pd.Timestamp,
    variable: str = "utci",
    title: str = "",
    show: bool = True,
) -> plt.Figure:
    """Static scatter map using matplotlib.

    Plots a scatter with dots coloured by UTCI stress category on a plain
    axis (no basemap dependency). Useful for quick checks and reproducible
    figures without a browser.
    """
    dt = _to_utc_hour(dt)

    lats, lons, vals, names = [], [], [], []
    for loc, df in locations_dfs:
        idx = df.index.get_indexer([dt], method="nearest")[0]
        row = df.iloc[idx]
        val = row.get(variable, np.nan)
        lats.append(loc.lat)
        lons.append(loc.lon)
        vals.append(val)
        names.append(str(loc))

    colors = [_utci_color(v) for v in vals]

    fig, ax = plt.subplots(figsize=(10, 6))
    sc = ax.scatter(lons, lats, c=colors, s=200, edgecolors="white", linewidths=1.5, zorder=3)

    for name, lon, lat, val in zip(names, lons, lats, vals):
        ax.annotate(
            f"{name}\n{val:.1f}°C",
            xy=(lon, lat),
            xytext=(6, 6),
            textcoords="offset points",
            fontsize=7.5,
            ha="left",
        )

    ax.set_xlabel("Longitudine")
    ax.set_ylabel("Latitudine")
    ax.grid(alpha=0.3)

    # Ensure all points are visible with some padding
    if lons and lats:
        lon_pad = max(0.3, (max(lons) - min(lons)) * 0.2 + 0.1)
        lat_pad = max(0.2, (max(lats) - min(lats)) * 0.2 + 0.1)
        ax.set_xlim(min(lons) - lon_pad, max(lons) + lon_pad)
        ax.set_ylim(min(lats) - lat_pad, max(lats) + lat_pad)

    # Legend
    from matplotlib.patches import Patch
    legend_handles = [
        Patch(color=UTCI_COLORS[cat], label=cat, alpha=0.85)
        for cat in UTCI_CATEGORIES
    ]
    ax.legend(handles=legend_handles, fontsize=7, loc="lower left",
              title="UTCI stress", title_fontsize=7)

    dt_str = dt.strftime("%Y-%m-%d %H:%M UTC")
    ax.set_title(title or f"Thermal Comfort Map — {dt_str}")
    fig.tight_layout()

    if show:
        plt.show()
    return fig


# ── Internal helpers ──────────────────────────────────────────────────────────

def _to_utc_hour(ts: pd.Timestamp) -> pd.Timestamp:
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.floor("h")


def _build_popup(
    name: str,
    row: pd.Series,
    value: float,
    variable: str,
    category: str,
) -> str:
    def _fmt(v):
        return f"{v:.1f}" if pd.notna(v) else "—"

    lines = [
        f"<b style='font-size:13px'>{name}</b><br>",
        f"<b>UTCI:</b> {_fmt(row.get('utci'))} °C",
        f"<small><i>{row.get('utci_category', '')}</i></small><br>",
        f"<b>Temp. aria:</b> {_fmt(row.get('temperature_2m'))} °C<br>",
        f"<b>Umidità:</b> {_fmt(row.get('relative_humidity_2m'))} %<br>",
        f"<b>Vento:</b> {_fmt(row.get('wind_speed_10m'))} m/s<br>",
        f"<b>MRT:</b> {_fmt(row.get('mrt'))} °C<br>",
    ]
    if pd.notna(row.get("heat_index")):
        lines.append(f"<b>Heat Index:</b> {_fmt(row.get('heat_index'))} °C<br>")
    return "".join(lines)


def _add_utci_legend(m: folium.Map) -> None:
    items = "".join(
        f'<li><span style="background:{UTCI_COLORS[cat]};display:inline-block;'
        f'width:14px;height:14px;margin-right:5px;border-radius:2px"></span>{cat}</li>'
        for cat in UTCI_CATEGORIES
    )
    legend_html = (
        '<div style="position:fixed;bottom:30px;right:10px;'
        'background:rgba(255,255,255,0.92);padding:10px 14px;'
        'border-radius:8px;font-size:11px;z-index:1000;'
        'box-shadow:0 2px 8px rgba(0,0,0,0.25);max-width:240px">'
        '<b>UTCI Stress Category</b>'
        f'<ul style="margin:4px 0 0 0;padding:0;list-style:none">{items}</ul>'
        '</div>'
    )
    m.get_root().html.add_child(folium.Element(legend_html))
