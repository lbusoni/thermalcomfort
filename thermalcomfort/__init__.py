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
]

# Convenience alias
Location = LocationInfo


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
        """Fetch reanalysis (ERA5) and forecast data and compare them.

        The 'forecast' is the Open-Meteo forecast model output for the same
        period; the 'actual' is the ERA5 reanalysis archive.  This shows the
        typical forecast error you can expect.

        Note: both data sources are available only for past dates that are
        within the Open-Meteo archive (roughly the last 3 months via the
        forecast endpoint).
        """
        from .providers.open_meteo import OpenMeteoProvider

        start_ts = _parse_ts(start)
        end_ts = _parse_ts(end)

        # ERA5 archive — treated as ground truth
        archive_provider = OpenMeteoProvider()
        archive_cache = FileCache(archive_provider, None)
        actual_raw = archive_cache.get(location, start_ts, end_ts)
        actual = calculate_comfort(actual_raw, location.lat, location.lon, params)

        # Forecast model output for the same period (past_days parameter)
        from .providers.open_meteo import FORECAST_URL, HOURLY_VARIABLES
        import requests

        today = pd.Timestamp.now("UTC").normalize()
        past_days = (today - start_ts).days + 1

        resp = requests.get(
            FORECAST_URL,
            params={
                "latitude": location.lat,
                "longitude": location.lon,
                "hourly": ",".join(HOURLY_VARIABLES),
                "timezone": "UTC",
                "wind_speed_unit": "ms",
                "past_days": min(past_days, 92),
                "forecast_days": 1,
                "models": "ecmwf_ifs025",
            },
            timeout=60,
        )
        resp.raise_for_status()
        forecast_raw = OpenMeteoProvider._get_and_parse(resp.json())  # type: ignore[attr-defined]
        forecast_raw = forecast_raw[(forecast_raw.index >= start_ts) & (forecast_raw.index <= end_ts)]
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
