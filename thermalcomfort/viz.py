"""Plotting utilities for thermal comfort data."""

from typing import Optional, Sequence

import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .comfort.indices import UTCI_CATEGORIES, UTCI_COLORS

# Common figure size
FIG_W, FIG_H = 14, 5


def plot_timeseries(
    df: pd.DataFrame,
    title: str = "",
    local_tz: Optional[str] = None,
    show: bool = True,
) -> plt.Figure:
    """Plot UTCI, temperature, and raw variables for a single location.

    Parameters
    ----------
    df : pd.DataFrame
        Output of calculate_comfort(), UTC-indexed.
    title : str
        Figure title.
    local_tz : str, optional
        Timezone name (e.g. 'Europe/Rome') to convert the x-axis to local time.
    show : bool
        Call plt.show() if True.
    """
    index = _maybe_localise(df.index, local_tz)

    has_utci = "utci" in df.columns
    n_rows = 3 if has_utci else 2
    fig, axes = plt.subplots(n_rows, 1, figsize=(FIG_W, n_rows * FIG_H), sharex=True)

    ax_temp, ax_hum, *rest = axes
    ax_utci = rest[0] if rest else None

    # ---- Temperature + MRT ----
    ax_temp.plot(index, df["temperature_2m"], label="Air temp (2 m)", color="#2196F3", lw=1.5)
    if "mrt" in df.columns:
        ax_temp.plot(index, df["mrt"], label="MRT", color="#FF9800", lw=1.2, alpha=0.8)
    ax_temp.set_ylabel("Temperature [°C]")
    ax_temp.legend(fontsize=8, loc="upper left")
    ax_temp.grid(True, alpha=0.3)

    # ---- Humidity + wind ----
    color_rh = "#4CAF50"
    color_ws = "#9C27B0"
    ax2 = ax_hum.twinx()
    ax_hum.plot(index, df["relative_humidity_2m"], label="RH", color=color_rh, lw=1.2)
    ax_hum.set_ylabel("Relative humidity [%]", color=color_rh)
    ax_hum.tick_params(axis="y", labelcolor=color_rh)
    if "wind_speed_10m" in df.columns:
        ax2.plot(index, df["wind_speed_10m"], label="Wind (10 m)", color=color_ws, lw=1.0, alpha=0.7)
        ax2.set_ylabel("Wind speed [m/s]", color=color_ws)
        ax2.tick_params(axis="y", labelcolor=color_ws)
    ax_hum.grid(True, alpha=0.3)

    # ---- UTCI with category background ----
    if ax_utci is not None and has_utci:
        utci_vals = df["utci"].to_numpy(dtype=float)
        cats = df["utci_category"].to_numpy()
        _plot_utci_with_bands(ax_utci, index, utci_vals, cats)
        ax_utci.set_ylabel("UTCI [°C]")
        ax_utci.grid(True, alpha=0.3)
        _add_utci_legend(ax_utci)

    _format_time_axis(axes[-1])
    fig.suptitle(title, fontsize=12, y=1.01)
    fig.tight_layout()

    if show:
        plt.show()
    return fig


def plot_comparison(
    datasets: Sequence[pd.DataFrame],
    labels: Sequence[str],
    variable: str = "utci",
    local_tz: Optional[str] = None,
    title: str = "",
    show: bool = True,
) -> plt.Figure:
    """Compare a variable across multiple locations on the same axis.

    Parameters
    ----------
    datasets : list of DataFrames
        One per location (UTC-indexed, output of calculate_comfort).
    labels : list of str
        Location names, one per dataset.
    variable : str
        Column to compare (e.g. 'utci', 'temperature_2m', 'heat_index').
    local_tz : str, optional
        Timezone for x-axis display.
    title : str
        Figure title.
    show : bool
        Call plt.show() if True.
    """
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

    for df, label in zip(datasets, labels):
        if variable not in df.columns:
            continue
        index = _maybe_localise(df.index, local_tz)
        ax.plot(index, df[variable], label=label, lw=1.5, alpha=0.85)

    ylabel = _pretty_label(variable)
    ax.set_ylabel(ylabel)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    _format_time_axis(ax)
    fig.suptitle(title or f"Comparison — {ylabel}", fontsize=12)
    fig.tight_layout()

    if show:
        plt.show()
    return fig


def plot_comfort_summary(
    df: pd.DataFrame,
    label: str = "",
    show: bool = True,
) -> plt.Figure:
    """Stacked bar chart showing fraction of time in each UTCI category."""
    if "utci_category" not in df.columns:
        raise ValueError("DataFrame must contain 'utci_category' column.")

    counts = df["utci_category"].value_counts()
    total = counts.sum()
    fractions = counts / total

    # Order by UTCI range
    ordered = [c for c in UTCI_CATEGORIES if c in fractions.index]

    fig, ax = plt.subplots(figsize=(8, 3))
    left = 0.0
    for cat in ordered:
        frac = fractions.get(cat, 0.0)
        ax.barh(0, frac, left=left, color=UTCI_COLORS.get(cat, "#ccc"), height=0.6, label=cat)
        if frac > 0.04:
            ax.text(left + frac / 2, 0, f"{frac:.0%}", ha="center", va="center", fontsize=7)
        left += frac

    ax.set_xlim(0, 1)
    ax.set_yticks([])
    ax.set_xlabel("Fraction of time")
    ax.legend(
        handles=[mpatches.Patch(color=UTCI_COLORS[c], label=c) for c in ordered],
        bbox_to_anchor=(1.01, 1),
        loc="upper left",
        fontsize=7,
    )
    ax.set_title(label or "UTCI comfort distribution")
    fig.tight_layout()

    if show:
        plt.show()
    return fig


def plot_forecast_vs_actual(
    forecast: pd.DataFrame,
    actual: pd.DataFrame,
    variable: str = "utci",
    label: str = "",
    local_tz: Optional[str] = None,
    show: bool = True,
) -> plt.Figure:
    """Overlay forecast and actual values to visualise model accuracy.

    Parameters
    ----------
    forecast : pd.DataFrame
        Forecast data (e.g. fetched N days ahead).
    actual : pd.DataFrame
        Observed / reanalysis data for the same period.
    variable : str
        Column to compare.
    """
    fig, (ax_main, ax_err) = plt.subplots(2, 1, figsize=(FIG_W, 8), sharex=True)

    common_idx = forecast.index.intersection(actual.index)
    f_vals = forecast.loc[common_idx, variable]
    a_vals = actual.loc[common_idx, variable]
    err = f_vals - a_vals

    plot_idx = _maybe_localise(common_idx, local_tz)

    ax_main.plot(plot_idx, a_vals.values, label="Actual (ERA5)", color="#2196F3", lw=1.5)
    ax_main.plot(plot_idx, f_vals.values, label="Forecast", color="#FF5722", lw=1.2, ls="--", alpha=0.85)
    ax_main.set_ylabel(_pretty_label(variable))
    ax_main.legend(fontsize=8)
    ax_main.grid(True, alpha=0.3)

    ax_err.axhline(0, color="k", lw=0.8)
    ax_err.fill_between(plot_idx, err.values, alpha=0.4, color="#FF5722")
    ax_err.plot(plot_idx, err.values, color="#FF5722", lw=0.8)
    ax_err.set_ylabel("Forecast − Actual")
    ax_err.grid(True, alpha=0.3)

    mae = np.nanmean(np.abs(err))
    bias = np.nanmean(err)
    ax_err.set_title(f"Error  |  MAE = {mae:.2f}  |  bias = {bias:+.2f}", fontsize=9)

    _format_time_axis(ax_err)
    fig.suptitle(label or f"Forecast vs Actual — {_pretty_label(variable)}", fontsize=12)
    fig.tight_layout()

    if show:
        plt.show()
    return fig


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _maybe_localise(index: pd.DatetimeIndex, tz: Optional[str]) -> pd.DatetimeIndex:
    if tz:
        return index.tz_convert(tz)
    return index


def _format_time_axis(ax: plt.Axes) -> None:
    locator = mdates.AutoDateLocator()
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)
    plt.setp(ax.get_xticklabels(), rotation=0, ha="center")


def _plot_utci_with_bands(
    ax: plt.Axes,
    index: pd.DatetimeIndex,
    utci_vals: np.ndarray,
    cats: np.ndarray,
) -> None:
    """Draw UTCI line with coloured background bands per stress category."""
    for cat, (lo, hi) in UTCI_CATEGORIES.items():
        color = UTCI_COLORS.get(cat, "#ccc")
        ax.axhspan(lo, hi, alpha=0.12, color=color, lw=0)
    ax.plot(index, utci_vals, color="#333", lw=1.5, zorder=3)
    # Clamp y-axis to a readable range around actual values
    valid = utci_vals[~np.isnan(utci_vals)]
    if len(valid):
        pad = 5
        ax.set_ylim(min(valid.min() - pad, -5), max(valid.max() + pad, 35))


def _add_utci_legend(ax: plt.Axes) -> None:
    handles = [
        mpatches.Patch(color=UTCI_COLORS[c], label=c, alpha=0.6)
        for c in UTCI_CATEGORIES
    ]
    ax.legend(handles=handles, fontsize=6, loc="upper left", ncol=2)


def _pretty_label(col: str) -> str:
    labels = {
        "utci": "UTCI [°C]",
        "temperature_2m": "Air temperature [°C]",
        "mrt": "MRT [°C]",
        "heat_index": "Heat Index [°C]",
        "wind_chill": "Wind Chill [°C]",
        "wbgt_outdoor": "WBGT outdoor [°C]",
        "relative_humidity_2m": "Relative humidity [%]",
        "wind_speed_10m": "Wind speed [m/s]",
    }
    return labels.get(col, col)
