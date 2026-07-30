"""Provider for historical forecast model output.

Open-Meteo's forecast endpoint (with past_days) returns the most recent
model run for past dates, which approximates what was predicted at the time.
This is useful for forecast-vs-actual comparisons.
"""

import logging

import pandas as pd

from .base import LocationInfo, WeatherProvider
from .open_meteo import HOURLY_VARIABLES, OpenMeteoProvider

logger = logging.getLogger(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# Maximum days back the forecast endpoint supports
MAX_PAST_DAYS = 92


class ForecastModelProvider(WeatherProvider):
    """Fetches historical forecast-model output (not reanalysis) from Open-Meteo.

    Uses the forecast API with past_days, which returns recent model runs
    rather than the ERA5 reanalysis used by the archive endpoint.
    """

    name = "open_meteo_forecast"

    def fetch(
        self,
        location: LocationInfo,
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame:
        today = pd.Timestamp.now("UTC").normalize()
        past_days = (today - start).days + 1
        forecast_days = max(1, (end - today).days + 2)

        if past_days > MAX_PAST_DAYS:
            raise ValueError(
                f"ForecastModelProvider only supports up to {MAX_PAST_DAYS} days in "
                f"the past; requested {past_days} days."
            )

        params = {
            "latitude": location.lat,
            "longitude": location.lon,
            "hourly": ",".join(HOURLY_VARIABLES),
            "timezone": "UTC",
            "wind_speed_unit": "ms",
            "past_days": min(past_days, MAX_PAST_DAYS),
            "forecast_days": min(forecast_days, 16),
        }
        logger.debug("Forecast-model fetch for %s", location)
        df = OpenMeteoProvider._get_and_parse(FORECAST_URL, params)
        return df[(df.index >= start) & (df.index <= end)]
