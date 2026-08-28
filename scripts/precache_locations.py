#!/usr/bin/env python3
"""Pre-download weather data for known locations into the thermalcomfort cache.

Usage examples:
  python scripts/precache_locations.py
  python scripts/precache_locations.py --start 2015-01-01 --end 2025-12-31
  python scripts/precache_locations.py --locations Firenze Tucson "Los Angeles"
  python scripts/precache_locations.py --dry-run
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from thermalcomfort.cache import FileCache
from thermalcomfort.locations import LOCATIONS
from thermalcomfort.providers.open_meteo import OpenMeteoProvider


def _parse_ts(value: str) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts


def _build_parser() -> argparse.ArgumentParser:
    today_utc = pd.Timestamp.now("UTC").floor("h")
    default_start = pd.Timestamp("2010-01-01", tz="UTC")

    p = argparse.ArgumentParser(
        prog="precache_locations",
        description="Pre-populate thermalcomfort cache for known locations.",
    )
    p.add_argument(
        "--start",
        default=default_start.strftime("%Y-%m-%d"),
        help=f"Start datetime/date in UTC-parsable format (default: {default_start.date()})",
    )
    p.add_argument(
        "--end",
        default=today_utc.strftime("%Y-%m-%d %H:00"),
        help="End datetime/date in UTC-parsable format (default: current UTC hour)",
    )
    p.add_argument(
        "--locations",
        nargs="*",
        default=None,
        help="Optional subset of known location names.",
    )
    p.add_argument(
        "--cache-dir",
        default=None,
        help="Custom cache directory (default: ~/.thermalcomfort_cache)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned downloads without fetching data.",
    )
    return p


def _resolve_locations(selected_names: list[str] | None):
    if not selected_names:
        return sorted(LOCATIONS.items())

    unknown = [name for name in selected_names if name not in LOCATIONS]
    if unknown:
        known_preview = ", ".join(sorted(LOCATIONS)[:10])
        raise ValueError(
            f"Unknown location(s): {', '.join(unknown)}. "
            f"Use names from thermalcomfort locations (e.g. {known_preview})."
        )

    return [(name, LOCATIONS[name]) for name in selected_names]


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    start = _parse_ts(args.start)
    end = _parse_ts(args.end)
    if end < start:
        raise ValueError("--end must be >= --start")

    locations = _resolve_locations(args.locations)

    cache_dir = Path(args.cache_dir).expanduser() if args.cache_dir else None
    cache = FileCache(OpenMeteoProvider(), cache_dir=cache_dir)

    print(f"Preparing cache for {len(locations)} location(s)")
    print(f"Range: {start} -> {end}")
    if cache_dir is not None:
        print(f"Cache dir: {cache_dir}")

    if args.dry_run:
        for idx, (name, loc) in enumerate(locations, start=1):
            print(f"[{idx:02d}/{len(locations):02d}] {name}: {loc.lat:.4f},{loc.lon:.4f}")
        print("Dry run completed; no data downloaded.")
        return

    total_rows = 0
    for idx, (name, loc) in enumerate(locations, start=1):
        print(f"[{idx:02d}/{len(locations):02d}] Downloading {name} ...", flush=True)
        df = cache.get(loc, start, end)
        total_rows += len(df)
        print(f"     cached rows in range: {len(df)}")

    print(f"Done. Total rows cached across locations: {total_rows}")


if __name__ == "__main__":
    main()
