"""Climatological analysis — aggregations over multi-year ERA5 data.

Answers questions such as:
  - "Which month has the most comfortable weather in Florence?"
  - "Compare average July comfort in Rome vs Athens over 2010-2023."
  - "What does a typical August day look like hour-by-hour in Barcelona?"
"""

from __future__ import annotations

import logging
from typing import Callable, Optional, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from timezonefinder import TimezoneFinder
except ImportError:  # pragma: no cover - optional dependency
    TimezoneFinder = None

from .cache import FileCache
from .comfort.indices import ACTIVITY_MET, UTCI_CATEGORIES, UTCI_COLORS, ComfortParams, calculate_comfort
from .providers.base import LocationInfo
from .providers.open_meteo import OpenMeteoProvider


def _infer_timezone(location: Optional[LocationInfo] = None, timezone: Optional[str] = None) -> Optional[str]:
    """Resolve the timezone for a location, preferring an explicit override."""
    if timezone:
        return timezone
    if location is None or _TIMEZONE_FINDER is None:
        return None
    return _TIMEZONE_FINDER.timezone_at(lng=location.lon, lat=location.lat)


def _filter_daytime_hours(
    df: pd.DataFrame,
    timezone: Optional[str] = None,
    location: Optional[LocationInfo] = None,
) -> pd.DataFrame:
    """Keep hours between 07:00 and 19:00 in the requested local timezone."""
    if df.empty:
        return df

    target_tz = _infer_timezone(location=location, timezone=timezone)
    if target_tz is None:
        return df[(df.index.hour >= 7) & (df.index.hour <= 19)]

    local_df = df.copy()
    local_df.index = local_df.index.tz_convert(target_tz)
    local_hours = local_df.index.hour
    return local_df[(local_hours >= 7) & (local_hours <= 19)]

logger = logging.getLogger(__name__)

_TIMEZONE_FINDER = TimezoneFinder() if TimezoneFinder is not None else None

# Reference period used when none is specified
DEFAULT_START_YEAR = 2010
DEFAULT_END_YEAR = 2023

MONTHS_IT = [
    "Gen", "Feb", "Mar", "Apr", "Mag", "Giu",
    "Lug", "Ago", "Set", "Ott", "Nov", "Dic",
]

ACCEPTABLE_WARMTH_CATEGORIES = {
    "no thermal stress",
    "moderate heat stress",
}

HEAT_STRESS_CATEGORIES = {
    "strong heat stress",
    "very strong heat stress",
    "extreme heat stress",
}

COLD_STRESS_CATEGORIES = {
    "slight cold stress",
    "moderate cold stress",
    "strong cold stress",
    "very strong cold stress",
    "extreme cold stress",
}


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
        self._computed_cache: dict[tuple, pd.DataFrame] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def monthly_stats(
        self,
        location: LocationInfo,
        params: Optional[ComfortParams] = None,
        daytime_only: bool = True,
        timezone: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, int], None]] = None,
    ) -> pd.DataFrame:
        """Return mean/std UTCI and temperature per calendar month.

        Parameters
        ----------
        location : LocationInfo
        params : ComfortParams, optional
        daytime_only : bool
            If True, only 07-19 local-time hours are included.

        Returns
        -------
        pd.DataFrame indexed by month (1-12), columns:
            utci_mean, utci_std, temp_mean, temp_std,
            no_stress_frac, acceptable_warmth_frac,
            heat_stress_frac, cold_stress_frac
        """
        if params is None:
            params = ComfortParams()

        df = self._load_years(location, params, progress_callback=progress_callback)

        if daytime_only:
            df = _filter_daytime_hours(df, timezone=timezone, location=location)

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
                "acceptable_warmth_frac": cats.isin(ACCEPTABLE_WARMTH_CATEGORIES).mean(),
                "heat_stress_frac": cats.isin(HEAT_STRESS_CATEGORIES).mean(),
                "cold_stress_frac": cats.isin(COLD_STRESS_CATEGORIES).mean(),
            })

        return pd.DataFrame(rows).set_index("month")

    def hourly_profile(
        self,
        location: LocationInfo,
        month: int,
        params: Optional[ComfortParams] = None,
        timezone: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, int], None]] = None,
    ) -> pd.DataFrame:
        """Return mean comfort indices by hour-of-day for a specific month.

        Returns
        -------
        pd.DataFrame indexed 0-23, columns: utci_mean, utci_p25, utci_p75,
            temp_mean, rh_mean, wind_mean
        """
        if params is None:
            params = ComfortParams()

        df = self._load_years(location, params, progress_callback=progress_callback)
        month_df = df[df.index.month == month]
        resolved_tz = _infer_timezone(location=location, timezone=timezone)
        if resolved_tz is not None and not month_df.empty:
            month_df = month_df.copy()
            month_df.index = month_df.index.tz_convert(resolved_tz)

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
        timezone: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, int], None]] = None,
    ) -> pd.DataFrame:
        """Rank locations by acceptable daytime thermal stress conditions.

        The ranking score is the fraction of daytime hours in either
        "no thermal stress" or "moderate heat stress".

        Returns
        -------
        pd.DataFrame with columns: location, utci_mean, acceptable_warmth_frac,
            ranked by acceptable_warmth_frac descending.
        """
        if params is None:
            params = ComfortParams()

        rows = []
        for loc in locations:
            try:
                df = self._load_years(loc, params, progress_callback=progress_callback)
                if month:
                    df = df[df.index.month == month]
                if daytime_only:
                    df = _filter_daytime_hours(df, timezone=timezone, location=loc)
                utci = df["utci"].dropna()
                cats = df["utci_category"]
                rows.append({
                    "location": str(loc),
                    "utci_mean": utci.mean(),
                    "utci_std": utci.std(),
                    "no_stress_frac": (cats == "no thermal stress").mean(),
                    "acceptable_warmth_frac": cats.isin(ACCEPTABLE_WARMTH_CATEGORIES).mean(),
                    "heat_stress_frac": cats.isin(HEAT_STRESS_CATEGORIES).mean(),
                    "cold_stress_frac": cats.isin(COLD_STRESS_CATEGORIES).mean(),
                })
            except Exception as exc:
                logger.warning("Could not process %s: %s", loc, exc)

        result = pd.DataFrame(rows)
        if not result.empty:
            result = result.sort_values("acceptable_warmth_frac", ascending=False).reset_index(drop=True)
        return result

    # ------------------------------------------------------------------
    # Plotting
    # ------------------------------------------------------------------

    def plot_monthly(
        self,
        location: LocationInfo,
        params: Optional[ComfortParams] = None,
        show: bool = True,
        progress_callback: Optional[Callable[[int, int, int], None]] = None,
    ) -> plt.Figure:
        """Bar chart of mean UTCI ± std per month, stacked stress-fraction bar."""
        stats = self.monthly_stats(
            location, params=params, progress_callback=progress_callback
        )
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
        _set_utci_axis_limits(ax1, stats["utci_mean"].to_numpy(dtype=float))

        # ── Stress fraction stacked bar ────────────────────────────────
        acceptable = stats["acceptable_warmth_frac"].to_numpy(dtype=float)
        heat = stats["heat_stress_frac"].to_numpy(dtype=float)
        cold = stats["cold_stress_frac"].to_numpy(dtype=float)
        other = np.clip(1.0 - acceptable - heat - cold, 0.0, 1.0)

        ax2.bar(months, acceptable, color=UTCI_COLORS["no thermal stress"], alpha=0.85, label="poco stress (ok + caldo moderato)")
        ax2.bar(months, heat,       color=UTCI_COLORS["strong heat stress"], alpha=0.85, bottom=acceptable, label="stress da caldo forte+")
        ax2.bar(months, cold,       color=UTCI_COLORS["moderate cold stress"], alpha=0.85, bottom=acceptable + heat, label="stress da freddo (da lieve)")
        ax2.bar(months, other,      color="#ccc", alpha=0.6, bottom=acceptable + heat + cold, label="altro")
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
        timezone: Optional[str] = None,
        show: bool = True,
        progress_callback: Optional[Callable[[int, int, int], None]] = None,
    ) -> plt.Figure:
        """Shaded mean ± IQR UTCI curve over a typical day for a given month."""
        profile = self.hourly_profile(
            location,
            month=month,
            params=params,
            timezone=timezone,
            progress_callback=progress_callback,
        )
        hours = profile.index
        resolved_tz = _infer_timezone(location=location, timezone=timezone)

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
        ax.set_xlabel(f"Ora ({resolved_tz or timezone or 'UTC'})")
        ax.set_ylabel("°C")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
        _set_utci_axis_limits(ax, profile["utci_mean"].to_numpy(dtype=float))
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
        ax.barh(y, df["acceptable_warmth_frac"], color=colors, alpha=0.85)
        ax.set_yticks(list(y))
        ax.set_yticklabels(df["location"])
        ax.set_xlabel("Frazione ore diurne con stress accettabile")
        ax.set_xlim(0, 1)
        for i, (_, row) in enumerate(df.iterrows()):
            ax.text(row["acceptable_warmth_frac"] + 0.01, i,
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
        progress_callback: Optional[Callable[[int, int, int], None]] = None,
    ) -> pd.DataFrame:
        """Fetch and concatenate ERA5 data for all years, compute comfort."""
        cache_key = (
            location.cache_key(),
            self.start_year,
            self.end_year,
            params.met,
            float(params.sun_exposure),
            params.posture,
        )
        cached = self._computed_cache.get(cache_key)
        if cached is not None:
            return cached

        frames = []
        years = list(range(self.start_year, self.end_year + 1))
        total = len(years)
        for i, year in enumerate(years, start=1):
            if progress_callback is not None:
                progress_callback(i, total, year)
            start = pd.Timestamp(f"{year}-01-01", tz="UTC")
            end = pd.Timestamp(f"{year}-12-31 23:00", tz="UTC")
            logger.info("Loading %d for %s …", year, location)
            raw = self._cache.get(location, start, end)
            cf = calculate_comfort(raw, lat=location.lat, lon=location.lon, params=params)
            frames.append(cf)
        merged = pd.concat(frames).sort_index()
        self._computed_cache[cache_key] = merged
        return merged


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _empty_row(month: int) -> dict:
    return {
        "month": month,
        "utci_mean": np.nan, "utci_std": np.nan,
        "temp_mean": np.nan, "temp_std": np.nan,
        "no_stress_frac": np.nan,
        "acceptable_warmth_frac": np.nan,
        "heat_stress_frac": np.nan,
        "cold_stress_frac": np.nan,
    }


def _utci_month_color(utci_val: float) -> str:
    """Return the UTCI colour for a given value."""
    for cat, (lo, hi) in UTCI_CATEGORIES.items():
        if lo <= utci_val < hi:
            return UTCI_COLORS[cat]
    return "#aaa"


def _set_utci_axis_limits(ax: plt.Axes, values: np.ndarray) -> None:
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        ax.set_ylim(-10, 40)
        return

    vmin = float(np.nanmin(finite))
    vmax = float(np.nanmax(finite))
    pad = max(3.0, 0.15 * (vmax - vmin))
    lower = max(-35.0, vmin - pad)
    upper = min(60.0, vmax + pad)
    if upper - lower < 10:
        lower -= 5
        upper += 5
    ax.set_ylim(lower, upper)
