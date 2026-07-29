"""Climatological analysis — aggregations over multi-year ERA5 data.

Answers questions such as:
  - "Which month has the most comfortable weather in Florence?"
  - "Compare average July comfort in Rome vs Athens over 2010-2023."
  - "What does a typical August day look like hour-by-hour in Barcelona?"
"""

from __future__ import annotations

import logging
from typing import Optional, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .cache import FileCache
from .comfort.indices import ACTIVITY_MET, UTCI_CATEGORIES, UTCI_COLORS, ComfortParams, calculate_comfort
from .providers.base import LocationInfo
from .providers.open_meteo import OpenMeteoProvider

logger = logging.getLogger(__name__)

# Reference period used when none is specified
DEFAULT_START_YEAR = 2010
DEFAULT_END_YEAR = 2023

MONTHS_IT = [
    "Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
    "Lug", "Ago", "Set", "Ott", "Nov", "Dic",
]


class ClimateAnalysis:
    """Fetch and aggregate multi-year ERA5 data for climatological summaries.

    Parameters
    ----------
    cache_dir : path-like, optional
        Directory for the weather data cache.
    start_year, end_year : int
        Inclusive year range for climatological averages.
    """

    def __init__(
        self,
        cache_dir=None,
        start_year: int = DEFAULT_START_YEAR,
        end_year: int = DEFAULT_END_YEAR,
    ) -> None:
        self._cache = FileCache(OpenMeteoProvider(), cache_dir)
        self.start_year = start_year
        self.end_year = end_year

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def monthly_stats(
        self,
        location: LocationInfo,
        params: Optional[ComfortParams] = None,
        daytime_only: bool = True,
    ) -> pd.DataFrame:
        """Return mean/std UTCI and temperature per calendar month.

        Parameters
        ----------
        location : LocationInfo
        params : ComfortParams, optional
        daytime_only : bool
            If True, only 07-19 UTC hours are included (avoid night distortion).

        Returns
        -------
        pd.DataFrame indexed by month (1-12), columns:
            utci_mean, utci_std, temp_mean, temp_std,
            no_stress_frac, heat_stress_frac, cold_stress_frac
        """
        if params is None:
            params = ComfortParams()

        df = self._load_years(location, params)

        if daytime_only:
            df = df[(df.index.hour >= 7) & (df.index.hour <= 19)]

        rows = []
        for month in range(1, 13):
            m = df[df.index.month == month]
            if m.empty:
                rows.append(_empty_row(month))
                continue

            utci = m["utci"].dropna()
            cats = m["utci_category"]
            rows.append({
                "month": month,
                "utci_mean": utci.mean(),
                "utci_std": utci.std(),
                "temp_mean": m["temperature_2m"].mean(),
                "temp_std": m["temperature_2m"].std(),
                "no_stress_frac": (cats == "no thermal stress").mean(),
                "heat_stress_frac": cats.str.contains("heat stress").mean(),
                "cold_stress_frac": cats.str.contains("cold stress").mean(),
            })

        return pd.DataFrame(rows).set_index("month")

    def hourly_profile(
        self,
        location: LocationInfo,
        month: int,
        params: Optional[ComfortParams] = None,
    ) -> pd.DataFrame:
        """Return mean comfort indices by hour-of-day for a specific month.

        Returns
        -------
        pd.DataFrame indexed 0-23, columns: utci_mean, utci_p25, utci_p75,
            temp_mean, rh_mean, wind_mean
        """
        if params is None:
            params = ComfortParams()

        df = self._load_years(location, params)
        month_df = df[df.index.month == month]

        rows = []
        for hour in range(24):
            h = month_df[month_df.index.hour == hour]
            rows.append({
                "hour": hour,
                "utci_mean": h["utci"].mean(),
                "utci_p25": h["utci"].quantile(0.25),
                "utci_p75": h["utci"].quantile(0.75),
                "temp_mean": h["temperature_2m"].mean(),
                "rh_mean": h["relative_humidity_2m"].mean(),
                "wind_mean": h["wind_speed_10m"].mean(),
            })
        return pd.DataFrame(rows).set_index("hour")

    def rank_locations(
        self,
        locations: Sequence[LocationInfo],
        month: Optional[int] = None,
        params: Optional[ComfortParams] = None,
        daytime_only: bool = True,
    ) -> pd.DataFrame:
        """Rank locations by how close their average UTCI is to 'no thermal stress'.

        The "comfort score" is the fraction of daytime hours in the no-thermal-stress
        band (9-26 °C UTCI).

        Returns
        -------
        pd.DataFrame with columns: location, utci_mean, no_stress_frac,
            ranked by no_stress_frac descending.
        """
        if params is None:
            params = ComfortParams()

        rows = []
        for loc in locations:
            try:
                df = self._load_years(loc, params)
                if month:
                    df = df[df.index.month == month]
                if daytime_only:
                    df = df[(df.index.hour >= 7) & (df.index.hour <= 19)]
                utci = df["utci"].dropna()
                cats = df["utci_category"]
                rows.append({
                    "location": str(loc),
                    "utci_mean": utci.mean(),
                    "utci_std": utci.std(),
                    "no_stress_frac": (cats == "no thermal stress").mean(),
                    "heat_stress_frac": cats.str.contains("heat stress").mean(),
                    "cold_stress_frac": cats.str.contains("cold stress").mean(),
                })
            except Exception as exc:
                logger.warning("Could not process %s: %s", loc, exc)

        result = pd.DataFrame(rows)
        if not result.empty:
            result = result.sort_values("no_stress_frac", ascending=False).reset_index(drop=True)
        return result

    # ------------------------------------------------------------------
    # Plotting
    # ------------------------------------------------------------------

    def plot_monthly(
        self,
        location: LocationInfo,
        params: Optional[ComfortParams] = None,
        show: bool = True,
    ) -> plt.Figure:
        """Bar chart of mean UTCI ± std per month, stacked stress-fraction bar."""
        stats = self.monthly_stats(location, params=params)
        months = range(1, 13)

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True)

        # ── Mean UTCI ± std ────────────────────────────────────────────
        colors = [_utci_month_color(v) for v in stats["utci_mean"]]
        ax1.bar(months, stats["utci_mean"], color=colors, alpha=0.85, zorder=2)
        ax1.errorbar(
            months, stats["utci_mean"], yerr=stats["utci_std"],
            fmt="none", color="#333", capsize=4, lw=1.2, zorder=3,
        )
        # Horizontal bands for stress categories
        for cat, (lo, hi) in UTCI_CATEGORIES.items():
            ax1.axhspan(lo, hi, alpha=0.07, color=UTCI_COLORS[cat], lw=0)
        ax1.set_ylabel("UTCI medio diurno [°C]")
        ax1.set_title(f"Profilo climatologico — {location}  ({self.start_year}–{self.end_year})")
        ax1.grid(axis="y", alpha=0.3)
        ax1.set_ylim(
            min(stats["utci_mean"].min() - 10, -5),
            max(stats["utci_mean"].max() + 10, 35),
        )

        # ── Stress fraction stacked bar ────────────────────────────────
        no_stress = stats["no_stress_frac"].values
        heat = stats["heat_stress_frac"].values
        cold = stats["cold_stress_frac"].values
        other = 1 - no_stress - heat - cold

        ax2.bar(months, no_stress, color=UTCI_COLORS["no thermal stress"], alpha=0.85, label="nessuno stress")
        ax2.bar(months, heat,      color=UTCI_COLORS["strong heat stress"], alpha=0.85, bottom=no_stress, label="stress da caldo")
        ax2.bar(months, cold,      color=UTCI_COLORS["moderate cold stress"], alpha=0.85, bottom=no_stress + heat, label="stress da freddo")
        ax2.bar(months, other,     color="#ccc", alpha=0.6, bottom=no_stress + heat + cold, label="altro")
        ax2.set_ylabel("Frazione di ore")
        ax2.set_ylim(0, 1)
        ax2.legend(fontsize=8, loc="upper right")
        ax2.set_xticks(list(months))
        ax2.set_xticklabels(MONTHS_IT)
        ax2.grid(axis="y", alpha=0.3)

        fig.tight_layout()
        if show:
            plt.show()
        return fig

    def plot_hourly_profile(
        self,
        location: LocationInfo,
        month: int,
        params: Optional[ComfortParams] = None,
        show: bool = True,
    ) -> plt.Figure:
        """Shaded mean ± IQR UTCI curve over a typical day for a given month."""
        profile = self.hourly_profile(location, month=month, params=params)
        hours = profile.index

        fig, ax = plt.subplots(figsize=(10, 4))

        for cat, (lo, hi) in UTCI_CATEGORIES.items():
            ax.axhspan(lo, hi, alpha=0.09, color=UTCI_COLORS[cat], lw=0)

        ax.fill_between(hours, profile["utci_p25"], profile["utci_p75"],
                        alpha=0.3, color="#1976D2", label="IQR 25-75%")
        ax.plot(hours, profile["utci_mean"], color="#1976D2", lw=2, label="Media UTCI")
        ax.plot(hours, profile["temp_mean"], color="#FF7043", lw=1.5, ls="--", label="Temp. aria")

        ax.set_xlim(0, 23)
        ax.set_xticks(range(0, 24, 2))
        ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 2)], rotation=30)
        ax.set_ylabel("°C")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
        month_name = MONTHS_IT[month - 1]
        ax.set_title(f"Profilo orario tipico — {location}, {month_name}  ({self.start_year}–{self.end_year})")

        fig.tight_layout()
        if show:
            plt.show()
        return fig

    def plot_rank(
        self,
        locations: Sequence[LocationInfo],
        month: Optional[int] = None,
        params: Optional[ComfortParams] = None,
        show: bool = True,
    ) -> plt.Figure:
        """Horizontal bar chart ranking locations by comfort."""
        df = self.rank_locations(locations, month=month, params=params)
        if df.empty:
            raise ValueError("No data available for ranking.")

        fig, ax = plt.subplots(figsize=(10, max(3, len(df) * 0.55)))
        colors = [_utci_month_color(v) for v in df["utci_mean"]]
        y = range(len(df))
        ax.barh(y, df["no_stress_frac"], color=colors, alpha=0.85)
        ax.set_yticks(list(y))
        ax.set_yticklabels(df["location"])
        ax.set_xlabel("Frazione ore senza stress termico (diurno)")
        ax.set_xlim(0, 1)
        for i, (_, row) in enumerate(df.iterrows()):
            ax.text(row["no_stress_frac"] + 0.01, i,
                    f"{row['utci_mean']:.1f}°C", va="center", fontsize=8)
        month_label = f" — {MONTHS_IT[month - 1]}" if month else ""
        ax.set_title(f"Classifica comfort{month_label}  ({self.start_year}–{self.end_year})")
        ax.grid(axis="x", alpha=0.3)
        fig.tight_layout()
        if show:
            plt.show()
        return fig

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_years(
        self,
        location: LocationInfo,
        params: ComfortParams,
    ) -> pd.DataFrame:
        """Fetch and concatenate ERA5 data for all years, compute comfort."""
        frames = []
        for year in range(self.start_year, self.end_year + 1):
            start = pd.Timestamp(f"{year}-01-01", tz="UTC")
            end = pd.Timestamp(f"{year}-12-31 23:00", tz="UTC")
            logger.info("Loading %d for %s …", year, location)
            raw = self._cache.get(location, start, end)
            cf = calculate_comfort(raw, lat=location.lat, lon=location.lon, params=params)
            frames.append(cf)
        return pd.concat(frames).sort_index()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _empty_row(month: int) -> dict:
    return {
        "month": month,
        "utci_mean": np.nan, "utci_std": np.nan,
        "temp_mean": np.nan, "temp_std": np.nan,
        "no_stress_frac": np.nan,
        "heat_stress_frac": np.nan,
        "cold_stress_frac": np.nan,
    }


def _utci_month_color(utci_val: float) -> str:
    """Return the UTCI colour for a given value."""
    for cat, (lo, hi) in UTCI_CATEGORIES.items():
        if lo <= utci_val < hi:
            return UTCI_COLORS[cat]
    return "#aaa"
