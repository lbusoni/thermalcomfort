"""Open-Meteo weather provider.

Uses the free Archive API (ERA5 reanalysis) for historical data and the
Forecast API for recent/future data, automatically choosing the right
endpoint based on the requested date range.
"""

import logging
from typing import Optional

import pandas as pd
import requests

from .base import LocationInfo, WeatherProvider

logger = logging.getLogger(__name__)

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# Archive data lags ~5 days behind today; we use a conservative margin.
ARCHIVE_LAG_DAYS = 6

# Variables requested from both APIs (all available on both endpoints).
HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "shortwave_radiation",
    "direct_normal_irradiance",
    "diffuse_radiation",
    "cloud_cover",
    "precipitation",
    "apparent_temperature",
]


class OpenMeteoProvider(WeatherProvider):
    """Fetches hourly weather data from the Open-Meteo API (no API key required)."""

    name = "open_meteo"

    def fetch(
        self,
        location: LocationInfo,
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame:
        today = pd.Timestamp.now("UTC").normalize()
        archive_cutoff = today - pd.Timedelta(days=ARCHIVE_LAG_DAYS)

        if end <= archive_cutoff:
            return self._fetch_archive(location, start, end)
        elif start > archive_cutoff:
            return self._fetch_forecast(location, start, end)
        else:
            # Requested range straddles the archive/forecast boundary.
            df_hist = self._fetch_archive(location, start, archive_cutoff)
            df_fcast = self._fetch_forecast(
                location, archive_cutoff + pd.Timedelta(hours=1), end
            )
            return pd.concat([df_hist, df_fcast]).sort_index()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_archive(
        self, location: LocationInfo, start: pd.Timestamp, end: pd.Timestamp
    ) -> pd.DataFrame:
        params = {
            "latitude": location.lat,
            "longitude": location.lon,
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
            "hourly": ",".join(HOURLY_VARIABLES),
            "timezone": "UTC",
            "wind_speed_unit": "ms",
        }
        logger.debug("Archive fetch %s → %s for %s", start.date(), end.date(), location)
        return self._get_and_parse(ARCHIVE_URL, params)

    def _fetch_forecast(
        self, location: LocationInfo, start: pd.Timestamp, end: pd.Timestamp
    ) -> pd.DataFrame:
        today = pd.Timestamp.now("UTC").normalize()
        past_days = max(0, (today - start).days + 1)
        forecast_days = max(1, (end - today).days + 2)

        params = {
            "latitude": location.lat,
            "longitude": location.lon,
            "hourly": ",".join(HOURLY_VARIABLES),
            "timezone": "UTC",
            "wind_speed_unit": "ms",
            "past_days": min(past_days, 92),
            "forecast_days": min(forecast_days, 16),
        }
        logger.debug(
            "Forecast fetch %s → %s for %s", start.date(), end.date(), location
        )
        df = self._get_and_parse(FORECAST_URL, params)
        return df[(df.index >= start) & (df.index <= end)]

    @staticmethod
    def _get_and_parse(url: str, params: dict) -> pd.DataFrame:
        resp = requests.get(url, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        if "hourly" not in data:
            raise ValueError(f"Unexpected Open-Meteo response: {data}")

        hourly = data["hourly"]
        times = pd.to_datetime(hourly.pop("time"))

        df = pd.DataFrame(hourly, index=times)
        df.index.name = "time"
        df.index = df.index.tz_localize("UTC")

        # Ensure all expected columns exist (fill missing with NaN)
        for col in HOURLY_VARIABLES:
            if col not in df.columns:
                df[col] = float("nan")

        return df
