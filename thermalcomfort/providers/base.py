from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import pandas as pd

# Columns that every provider must return
REQUIRED_COLUMNS = [
    "temperature_2m",        # Air temperature at 2 m, [°C]
    "relative_humidity_2m",  # Relative humidity at 2 m, [%]
    "wind_speed_10m",        # Wind speed at 10 m, [m/s]
]

# Columns used for solar MRT calculation and enrichment (may be NaN if unavailable)
OPTIONAL_COLUMNS = [
    "shortwave_radiation",       # Global horizontal irradiance, [W/m²]
    "direct_normal_irradiance",  # Direct normal (beam) irradiance, [W/m²]
    "diffuse_radiation",         # Diffuse horizontal irradiance, [W/m²]
    "cloud_cover",               # Cloud cover, [%]
    "precipitation",             # Precipitation, [mm]
    "apparent_temperature",      # Provider's own apparent temperature, [°C]
]


@dataclass
class LocationInfo:
    """Geographic location used for data requests."""

    lat: float
    lon: float
    name: str = ""

    def __str__(self) -> str:
        label = self.name or f"{self.lat:.3f}, {self.lon:.3f}"
        return label

    def cache_key(self) -> str:
        """Stable key for use in file names."""
        return f"{self.lat:.3f}_{self.lon:.3f}"


class WeatherProvider(ABC):
    """Abstract base class for weather data providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier for this provider (used in cache paths)."""
        ...

    @abstractmethod
    def fetch(
        self,
        location: LocationInfo,
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame:
        """
        Return hourly weather data for *location* between *start* and *end*
        (both UTC-aware).

        The returned DataFrame must:
        - be indexed by a UTC-aware DatetimeIndex named "time"
        - contain all REQUIRED_COLUMNS (NaN where truly unavailable)
        - contain as many OPTIONAL_COLUMNS as possible
        """
        ...
