"""thermalcomfort — Perceived thermal comfort visualisation system.

Quick start
-----------
>>> from thermalcomfort import ThermalComfortSystem, Location
>>> tcs = ThermalComfortSystem()
>>> florence = Location(lat=43.7696, lon=11.2558, name="Firenze")
>>> df = tcs.get(florence, start="2024-07-15", end="2024-07-15 23:00")
>>> tcs.plot(df)
"""

import logging
from pathlib import Path
from typing import Optional, Sequence, Union

import pandas as pd

from .cache import FileCache
from .comfort.indices import ComfortParams, calculate_comfort
from .locations import LOCATIONS, get_known_location, known_location_names
from .providers.base import LocationInfo
from .providers.open_meteo import OpenMeteoProvider
from .viz import (
    plot_comparison,
    plot_comfort_summary,
    plot_forecast_vs_actual,
    plot_timeseries,
)

__all__ = [
    "ThermalComfortSystem",
    "Location",
    "ComfortParams",
    "ClimateAnalysis",
    "LOCATIONS",
    "get_known_location",
    "known_location_names",
]

# Convenience alias
Location = LocationInfo

# Lazy import to avoid circular dependency
def __getattr__(name):
    if name == "ClimateAnalysis":
        from .climate import ClimateAnalysis as _CA
        return _CA
    raise AttributeError(f"module 'thermalcomfort' has no attribute {name!r}")


class ThermalComfortSystem:
    """High-level façade for fetching, computing, and plotting thermal comfort.

    Parameters
    ----------
    cache_dir : Path or str, optional
        Directory where downloaded weather data is cached.
        Defaults to ~/.thermalcomfort_cache/.
    log_level : int, optional
        Logging level for the thermalcomfort package (default: WARNING).
    """

    def __init__(
        self,
        cache_dir: Optional[Union[Path, str]] = None,
        log_level: int = logging.WARNING,
    ) -> None:
        logging.getLogger("thermalcomfort").setLevel(log_level)

        provider = OpenMeteoProvider()
        self._cache = FileCache(provider, cache_dir)

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------

    def get(
        self,
        location: LocationInfo,
        start: Union[str, pd.Timestamp],
        end: Union[str, pd.Timestamp],
        params: Optional[ComfortParams] = None,
        raw: bool = False,
    ) -> pd.DataFrame:
        """Fetch weather data and compute comfort indices for *location*.

        Parameters
        ----------
        location : Location
            Target location (lat, lon, optional name).
        start, end : str | pd.Timestamp
            Date/time range (inclusive). Strings are parsed by pandas; if no
            timezone is given UTC is assumed.
        params : ComfortParams, optional
            Activity level, sun exposure, posture.  See ComfortParams.
        raw : bool
            If True, return raw weather data without comfort calculation.

        Returns
        -------
        pd.DataFrame
            UTC-indexed DataFrame with weather variables and (unless raw=True)
            comfort indices: mrt, utci, utci_category, heat_index, wind_chill,
            wbgt_outdoor.
        """
        start_ts = _parse_ts(start)
        end_ts = _parse_ts(end)

        df = self._cache.get(location, start_ts, end_ts)

        if raw:
            return df

        return calculate_comfort(df, lat=location.lat, lon=location.lon, params=params)

    def compare(
        self,
        locations: Sequence[LocationInfo],
        start: Union[str, pd.Timestamp],
        end: Union[str, pd.Timestamp],
        variable: str = "utci",
        params: Optional[ComfortParams] = None,
        local_tz: Optional[str] = None,
        show: bool = True,
    ):
        """Fetch data for multiple locations and plot them on the same axis.

        Parameters
        ----------
        locations : list of Location
        start, end : str | Timestamp
        variable : str
            Column to compare (e.g. 'utci', 'temperature_2m').
        params : ComfortParams, optional
        local_tz : str, optional
            Timezone for the x-axis (e.g. 'Europe/Rome').
        show : bool
            Call plt.show() if True.
        """
        datasets = [self.get(loc, start, end, params=params) for loc in locations]
        labels = [str(loc) for loc in locations]
        return plot_comparison(
            datasets, labels, variable=variable, local_tz=local_tz, show=show
        )

    # ------------------------------------------------------------------
    # Plotting
    # ------------------------------------------------------------------

    def plot(
        self,
        df: pd.DataFrame,
        title: str = "",
        local_tz: Optional[str] = None,
        show: bool = True,
    ) -> "plt.Figure":
        """Plot full time-series dashboard for a single location."""
        return plot_timeseries(df, title=title, local_tz=local_tz, show=show)

    def plot_summary(
        self,
        df: pd.DataFrame,
        label: str = "",
        show: bool = True,
    ):
        """Stacked bar chart of UTCI stress category fractions."""
        return plot_comfort_summary(df, label=label, show=show)

    def plot_forecast_vs_actual(
        self,
        location: LocationInfo,
        start: Union[str, pd.Timestamp],
        end: Union[str, pd.Timestamp],
        variable: str = "utci",
        params: Optional[ComfortParams] = None,
        local_tz: Optional[str] = None,
        show: bool = True,
    ):
        """Fetch reanalysis (ERA5) and forecast model output and compare them.

        'actual' = ERA5 reanalysis (archive endpoint, ground truth).
        'forecast' = Open-Meteo forecast model output for the same past dates
          (using the forecast endpoint with past_days).

        Both sources are available for roughly the last 92 days.
        """
        from .providers.forecast_model import ForecastModelProvider

        start_ts = _parse_ts(start)
        end_ts = _parse_ts(end)

        # ERA5 archive — treated as ground truth (uses the shared cache)
        actual_raw = self._cache.get(location, start_ts, end_ts)
        actual = calculate_comfort(actual_raw, location.lat, location.lon, params)

        # Forecast model output — separate cache (different provider)
        forecast_cache = FileCache(ForecastModelProvider(), None)
        forecast_raw = forecast_cache.get(location, start_ts, end_ts)
        forecast = calculate_comfort(forecast_raw, location.lat, location.lon, params)

        return plot_forecast_vs_actual(
            forecast,
            actual,
            variable=variable,
            label=str(location),
            local_tz=local_tz,
            show=show,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_ts(value: Union[str, pd.Timestamp]) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts


# Lazy import for type hint only
try:
    import matplotlib.pyplot as plt
except ImportError:
    pass
