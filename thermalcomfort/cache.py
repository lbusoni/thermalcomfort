"""File-based cache for weather data.

Each (provider, location) pair is stored as a single Parquet file that grows
incrementally. On each request the cache:
  1. Loads existing data (if any).
  2. Identifies which hourly timestamps in [start, end] are still missing.
  3. Downloads missing data in monthly chunks (to minimise API round-trips).
  4. Merges and persists the updated dataset.
  5. Returns the slice covering [start, end].
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from .providers.base import LocationInfo, WeatherProvider

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path.home() / ".thermalcomfort_cache"


class FileCache:
    """Transparent caching layer wrapping a WeatherProvider."""

    def __init__(
        self,
        provider: WeatherProvider,
        cache_dir: Optional[Path] = None,
    ) -> None:
        self.provider = provider
        self.cache_dir = Path(cache_dir or DEFAULT_CACHE_DIR)

    def get(
        self,
        location: LocationInfo,
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame:
        """Return weather data for *location* in [start, end], fetching as needed."""
        start = _to_utc_hour(start)
        end = _to_utc_hour(end)

        cache_file = self._cache_path(location)
        existing = _load_parquet(cache_file)

        missing = _missing_timestamps(existing, start, end)

        if len(missing) > 0:
            logger.info(
                "%d missing hours for %s — fetching from %s",
                len(missing),
                location,
                self.provider.name,
            )
            for month_start, month_end in _monthly_chunks(missing):
                logger.debug("  downloading %s → %s", month_start.date(), month_end.date())
                new_data = self.provider.fetch(location, month_start, month_end)
                existing = _merge(existing, new_data)

            _save_parquet(cache_file, existing)
        else:
            logger.debug("Cache hit for %s [%s → %s]", location, start.date(), end.date())

        return existing[(existing.index >= start) & (existing.index <= end)].copy()

    def invalidate(self, location: LocationInfo) -> None:
        """Delete cached data for a location."""
        path = self._cache_path(location)
        if path.exists():
            path.unlink()
            logger.info("Cache invalidated for %s", location)

    def _cache_path(self, location: LocationInfo) -> Path:
        provider_dir = self.cache_dir / self.provider.name
        provider_dir.mkdir(parents=True, exist_ok=True)
        return provider_dir / f"{location.cache_key()}.parquet"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_utc_hour(ts: pd.Timestamp) -> pd.Timestamp:
    """Normalise timestamp to UTC and truncate to the hour."""
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts.floor("h")


def _load_parquet(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    if df.index.tzinfo is None:
        df.index = df.index.tz_localize("UTC")
    return df


def _save_parquet(path: Path, df: pd.DataFrame) -> None:
    if df is None or df.empty:
        return
    df.sort_index().to_parquet(path)


def _merge(existing: Optional[pd.DataFrame], new: pd.DataFrame) -> pd.DataFrame:
    if existing is None or existing.empty:
        return new
    combined = pd.concat([existing, new])
    # Keep the newest version of any duplicate timestamp.
    combined = combined[~combined.index.duplicated(keep="last")]
    return combined.sort_index()


def _missing_timestamps(
    existing: Optional[pd.DataFrame],
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DatetimeIndex:
    """Return hourly timestamps in [start, end] not present in *existing*."""
    full = pd.date_range(start, end, freq="h", tz="UTC")
    if existing is None or existing.empty:
        return full
    return full.difference(existing.index)


def _monthly_chunks(timestamps: pd.DatetimeIndex):
    """Yield (month_start, month_end) pairs covering all timestamps, one per month."""
    if len(timestamps) == 0:
        return
    # Strip timezone before converting to Period to avoid deprecation warning.
    months = timestamps.tz_localize(None).to_period("M").unique()
    for month in months:
        month_start = month.to_timestamp(how="start").tz_localize("UTC")
        # Last hour of the month
        month_end = (
            month.to_timestamp(how="end")
            .replace(minute=0, second=0, microsecond=0, nanosecond=0)
            .tz_localize("UTC")
        )
        yield month_start, month_end
