"""Command-line interface for the thermalcomfort package.

Usage
-----
    python -m thermalcomfort <subcommand> [options]

Subcommands
-----------
    show        Fetch and plot a single location
    compare     Compare multiple locations on the same chart
    summary     UTCI stress-category distribution for a period
    climate     Climatological monthly profile for a location
    rank        Rank predefined or given locations by comfort
    map         Build an interactive HTML map for a timestamp
    forecast    Forecast vs actual comparison plot
    locations   Print predefined known locations
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

import pandas as pd

# Hide noisy informational Intel OpenMP runtime warnings (not computation errors).
os.environ.setdefault("KMP_WARNINGS", "0")

COMMON_VARIABLE_CHOICES = [
    "utci",
    "utci_category",
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "mrt",
    "heat_index",
    "wind_chill",
    "wbgt_outdoor",
    "apparent_temperature",
    "precipitation",
    "cloud_cover",
    "shortwave_radiation",
    "direct_normal_irradiance",
    "diffuse_radiation",
]

MAP_VARIABLE_CHOICES = [
    "utci",
    "temperature_2m",
    "mrt",
    "heat_index",
    "wind_chill",
    "wbgt_outdoor",
    "apparent_temperature",
]

# ---------------------------------------------------------------------------
# Argument helpers
# ---------------------------------------------------------------------------

def _parse_location(s: str):
    """Accept 'Name:lat,lon' or 'lat,lon' or a known location key."""
    from thermalcomfort.providers.base import LocationInfo
    from thermalcomfort.locations import get_known_location, known_location_names

    if ":" in s:
        name, coords = s.split(":", 1)
        lat, lon = coords.split(",")
        return LocationInfo(float(lat), float(lon), name.strip())

    parts = s.split(",")
    if len(parts) == 2:
        return LocationInfo(float(parts[0]), float(parts[1]))

    try:
        return get_known_location(s)
    except KeyError as exc:
        preview = ", ".join(known_location_names()[:8])
        raise ValueError(
            f"Unknown location {s!r}. Use 'Name:lat,lon', 'lat,lon', or one of the known names (e.g. {preview})."
        ) from exc


def _parse_ts(s: str) -> pd.Timestamp:
    ts = pd.Timestamp(s)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts


# ---------------------------------------------------------------------------
# Sub-command handlers
# ---------------------------------------------------------------------------

def cmd_show(args):
    import matplotlib
    if not args.no_display:
        pass  # interactive
    else:
        matplotlib.use("Agg")

    from thermalcomfort import ComfortParams, ThermalComfortSystem
    from thermalcomfort.viz import plot_timeseries

    tcs = ThermalComfortSystem(log_level=10 if args.verbose else 30)
    loc = _parse_location(args.location)
    params = ComfortParams(activity=args.activity, sun_exposure=args.sun)

    print(f"Fetching data for {loc} from {args.start} to {args.end} …")
    df = tcs.get(loc, args.start, args.end, params=params)
    _print_summary(df, str(loc))

    fig = plot_timeseries(df, title=str(loc), local_tz=args.tz, show=False)
    if args.output:
        fig.savefig(args.output, dpi=150, bbox_inches="tight")
        print(f"Saved to {args.output}")
    else:
        import matplotlib.pyplot as plt
        plt.show()


def cmd_compare(args):
    import matplotlib
    if args.output:
        matplotlib.use("Agg")

    from thermalcomfort import ComfortParams, ThermalComfortSystem
    from thermalcomfort.viz import plot_comparison

    tcs = ThermalComfortSystem(log_level=10 if args.verbose else 30)
    locations = [_parse_location(l) for l in args.locations]
    params = ComfortParams(activity=args.activity, sun_exposure=args.sun)

    datasets = []
    for loc in locations:
        print(f"  Fetching {loc} …")
        datasets.append(tcs.get(loc, args.start, args.end, params=params))

    # Print comparison table at a specific hour if given
    if args.hour is not None:
        print(f"\n{'':4s} {'Location':25s} {'T [°C]':>8} {'UTCI [°C]':>10} {'Categoria'}")
        print("─" * 70)
        for loc, df in zip(locations, datasets):
            h = df[df.index.hour == int(args.hour)]
            if not h.empty:
                r = h.iloc[0]
                print(f"  {str(loc):25s} {r['temperature_2m']:8.1f} {r['utci']:10.1f}  {r['utci_category']}")

    labels = [str(l) for l in locations]
    fig = plot_comparison(datasets, labels, variable=args.variable,
                          local_tz=args.tz, title="Confronto", show=False)
    if args.output:
        fig.savefig(args.output, dpi=150, bbox_inches="tight")
        print(f"Saved to {args.output}")
    else:
        import matplotlib.pyplot as plt
        plt.show()


def cmd_summary(args):
    import matplotlib
    if args.output:
        matplotlib.use("Agg")

    from thermalcomfort import ComfortParams, ThermalComfortSystem
    from thermalcomfort.viz import plot_comfort_summary

    tcs = ThermalComfortSystem(log_level=10 if args.verbose else 30)
    loc = _parse_location(args.location)
    params = ComfortParams(activity=args.activity, sun_exposure=args.sun)

    df = tcs.get(loc, args.start, args.end, params=params)
    _print_summary(df, str(loc))

    fig = plot_comfort_summary(df, label=str(loc), show=False)
    if args.output:
        fig.savefig(args.output, dpi=150, bbox_inches="tight")
        print(f"Saved to {args.output}")
    else:
        import matplotlib.pyplot as plt
        plt.show()


def cmd_climate(args):
    import matplotlib
    if args.output:
        matplotlib.use("Agg")

    from thermalcomfort.climate import ClimateAnalysis
    loc = _parse_location(args.location)
    params_kw = dict(activity=args.activity, sun_exposure=args.sun)
    from thermalcomfort import ComfortParams
    params = ComfortParams(**params_kw)

    ca = ClimateAnalysis(
        start_year=int(args.start_year),
        end_year=int(args.end_year),
    )

    def _progress(i: int, total: int, year: int) -> None:
        width = 24
        filled = int(width * i / total)
        bar = "█" * filled + "░" * (width - filled)
        print(f"\rLoading years: [{bar}] {i}/{total}  (year {year})", end="", flush=True)

    print(f"Computing climatology for {loc} ({args.start_year}–{args.end_year}) …")
    stats = ca.monthly_stats(
        loc,
        params=params,
        timezone=args.tz,
        progress_callback=_progress,
    )
    print()
    tz_label = args.tz or "local time"
    print(f"\n Monthly UTCI statistics (daytime hours: 07:00–19:00, {tz_label})")
    print(stats.round(1).to_string())

    if args.month:
        fig = ca.plot_hourly_profile(
            loc,
            int(args.month),
            params=params,
            timezone=args.tz,
            show=False,
            progress_callback=_progress,
        )
    else:
        fig = ca.plot_monthly(
            loc,
            params=params,
            show=False,
            progress_callback=_progress,
        )

    if args.output:
        fig.savefig(args.output, dpi=150, bbox_inches="tight")
        print(f"Saved to {args.output}")
    else:
        import matplotlib.pyplot as plt
        plt.show()


def cmd_rank(args):
    import matplotlib
    if args.output:
        matplotlib.use("Agg")

    from thermalcomfort import ComfortParams
    from thermalcomfort.climate import ClimateAnalysis

    locations = [_parse_location(l) for l in args.locations]
    params = ComfortParams(activity=args.activity, sun_exposure=args.sun)
    ca = ClimateAnalysis(start_year=int(args.start_year), end_year=int(args.end_year))

    month = int(args.month) if args.month else None
    print("Computing rankings …")
    df = ca.rank_locations(
        locations,
        month=month,
        params=params,
        timezone=args.tz,
    )
    print("\n" + df.to_string())

    fig = ca.plot_rank(locations, month=month, params=params, show=False)
    if args.output:
        fig.savefig(args.output, dpi=150, bbox_inches="tight")
        print(f"Saved to {args.output}")
    else:
        import matplotlib.pyplot as plt
        plt.show()


def cmd_map(args):
    from thermalcomfort import ComfortParams, ThermalComfortSystem
    from thermalcomfort.mapview import build_map_from_locations, plot_map_static

    tcs = ThermalComfortSystem(log_level=10 if args.verbose else 30)
    locations = [_parse_location(l) for l in args.locations]
    params = ComfortParams(activity=args.activity, sun_exposure=args.sun)
    dt = _parse_ts(args.datetime)

    # Determine date range: ±1 day around the target timestamp
    start = (dt - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    end   = (dt + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"Fetching data for {len(locations)} locations around {dt} …")
    pairs = []
    for loc in locations:
        df = tcs.get(loc, start, end, params=params)
        pairs.append((loc, df))

    if args.static:
        import matplotlib
        if args.output:
            matplotlib.use("Agg")
        fig = plot_map_static(pairs, dt, variable=args.variable, show=False)
        if args.output:
            fig.savefig(args.output, dpi=150, bbox_inches="tight")
            print(f"Saved to {args.output}")
        else:
            import matplotlib.pyplot as plt
            plt.show()
    else:
        from pathlib import Path
        out = Path(args.output) if args.output else None
        path = build_map_from_locations(
            pairs, dt,
            variable=args.variable,
            output_path=out,
            open_browser=not bool(args.output),
        )
        print(f"Map saved to {path}")


def cmd_calc(args):
    """Calculate all comfort indices from directly supplied meteorological values."""
    import numpy as np
    from pythermalcomfort.models import (
        heat_index_rothfusz,
        solar_gain,
        utci,
        wind_chill_temperature,
    )

    from thermalcomfort.comfort.indices import (
        ACTIVITY_MET,
        ALPHA_SW,
        MIN_WIND_SPEED,
        UTCI_CATEGORIES,
        _wet_bulb_stull,
        _wbgt_outdoor,
    )

    ta  = args.temp
    rh  = args.rh
    ws  = args.wind

    # ── Mean Radiant Temperature ──────────────────────────────────────
    if args.mrt is not None:
        mrt = args.mrt
        mrt_note = "provided directly"
    elif args.solar is not None:
        sg = solar_gain(
            sol_altitude=args.solar_elevation,
            sharp=90.0,
            sol_radiation_dir=args.solar,
            sol_transmittance=1.0,
            f_svv=1.0,
            f_bes=args.sun,
            asw=ALPHA_SW,
            posture="standing",
            round_output=False,
        )
        mrt = ta + float(sg.delta_mrt)
        mrt_note = f"from solar gain (DNI={args.solar} W/m², elev={args.solar_elevation}°)"
    else:
        mrt = ta
        mrt_note = "= Ta  (shade / no solar data)"

    # ── Activity ──────────────────────────────────────────────────────
    met = ACTIVITY_MET[args.activity] if args.activity in ACTIVITY_MET else float(args.activity)
    act_label = f"{args.activity} ({met} MET)"

    # ── UTCI ──────────────────────────────────────────────────────────
    ws_eff = max(ws, MIN_WIND_SPEED)
    utci_res = utci(tdb=ta, tr=mrt, v=ws_eff, rh=rh, limit_inputs=False, round_output=False)
    utci_val = float(utci_res.utci)

    category = next(
        (label for label, (lo, hi) in UTCI_CATEGORIES.items() if lo <= utci_val < hi),
        "unknown",
    )

    # ── Heat Index ────────────────────────────────────────────────────
    if ta >= 27.0 and rh >= 40.0:
        hi_res = heat_index_rothfusz(tdb=ta, rh=rh, round_output=False)
        hi_str = f"{float(hi_res.hi):.1f} °C"
    else:
        hi_str = "n/a  (requires T ≥ 27 °C and RH ≥ 40 %)"

    # ── Wind Chill ────────────────────────────────────────────────────
    if ta <= 10.0 and ws >= 1.3:
        wc_res = wind_chill_temperature(tdb=ta, v=ws, round_output=False)
        wc_str = f"{float(wc_res.wct):.1f} °C"
    else:
        wc_str = "n/a  (requires T ≤ 10 °C and wind ≥ 1.3 m/s)"

    # ── Wet-bulb + WBGT ──────────────────────────────────────────────
    ta_a  = np.array([ta])
    rh_a  = np.array([rh])
    mrt_a = np.array([mrt])
    twb  = float(_wet_bulb_stull(ta_a, rh_a)[0])
    wbgt = float(_wbgt_outdoor(ta_a, rh_a, mrt_a)[0])

    # ── Print ─────────────────────────────────────────────────────────
    SEP = "─" * 58
    print(f"\n{SEP}")
    print("  Input conditions")
    print(SEP)
    print(f"  Air temperature:      {ta:.1f} °C")
    print(f"  Relative humidity:    {rh:.0f} %")
    print(f"  Wind speed (10 m):    {ws:.1f} m/s")
    print(f"  Mean radiant temp:    {mrt:.1f} °C  ({mrt_note})")
    print(f"  Activity:             {act_label}")
    print(f"  Sun exposure:         {args.sun}")
    print(f"\n{SEP}")
    print("  Comfort indices")
    print(SEP)
    print(f"  UTCI:                 {utci_val:.1f} °C  →  {category}")
    print(f"  Heat Index (NOAA):    {hi_str}")
    print(f"  Wind Chill (NWS):     {wc_str}")
    print(f"  WBGT outdoor:         {wbgt:.1f} °C")
    print(f"  Wet-bulb (Stull):     {twb:.1f} °C")
    print(f"{SEP}\n")


def cmd_forecast(args):
    import matplotlib
    if args.output:
        matplotlib.use("Agg")

    from thermalcomfort import ComfortParams, ThermalComfortSystem

    tcs = ThermalComfortSystem(log_level=10 if args.verbose else 30)
    loc = _parse_location(args.location)
    params = ComfortParams(activity=args.activity, sun_exposure=args.sun)

    fig = tcs.plot_forecast_vs_actual(
        loc, args.start, args.end,
        variable=args.variable,
        params=params,
        local_tz=args.tz,
        show=False,
    )
    if args.output:
        fig.savefig(args.output, dpi=150, bbox_inches="tight")
        print(f"Saved to {args.output}")
    else:
        import matplotlib.pyplot as plt
        plt.show()


def cmd_locations(args):
    from thermalcomfort.locations import LOCATIONS

    print(f"Known locations ({len(LOCATIONS)}):")
    for name in sorted(LOCATIONS):
        loc = LOCATIONS[name]
        print(f"- {name}:{loc.lat:.4f},{loc.lon:.4f}")


# ---------------------------------------------------------------------------
# Shared print helper
# ---------------------------------------------------------------------------

def _print_summary(df, label: str) -> None:
    if "utci" not in df.columns:
        return
    utci = df["utci"].dropna()
    cats = df["utci_category"]
    print(f"\n{'─'*60}")
    print(f"  {label}")
    print(f"  UTCI medio:  {utci.mean():.1f} °C  (min {utci.min():.1f} / max {utci.max():.1f})")
    print(f"  Temp. aria:  {df['temperature_2m'].mean():.1f} °C")
    print(f"  Senza stress termico:  {(cats == 'no thermal stress').mean():.0%}")
    print(f"  Stress da caldo:       {cats.str.contains('heat stress').mean():.0%}")
    print(f"  Stress da freddo:      {cats.str.contains('cold stress').mean():.0%}")
    print(f"{'─'*60}\n")


# ---------------------------------------------------------------------------
# Shared arguments factory
# ---------------------------------------------------------------------------

def _add_common(p: argparse.ArgumentParser, *, dates: bool = True) -> None:
    if dates:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        week_ago = (pd.Timestamp.now("UTC") - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
        p.add_argument("--start", default=week_ago, metavar="DATE",
                       help="Start date/time (default: 7 days ago)")
        p.add_argument("--end",   default=today,    metavar="DATE",
                       help="End date/time (default: today)")
    p.add_argument("--activity", default="walking",
                   choices=["resting", "seated", "standing", "walking",
                             "walking_fast", "hiking", "cycling"],
                   help="Activity level (default: walking)")
    p.add_argument("--sun", type=float, default=0.5, metavar="0-1",
                   help="Sun exposure fraction 0=shade … 1=full sun (default: 0.5)")
    p.add_argument("--tz", default=None, metavar="TZ",
                   help="Local timezone for x-axis (e.g. Europe/Rome)")
    p.add_argument("--output", "-o", default=None, metavar="FILE",
                   help="Save figure to file instead of displaying")
    p.add_argument("--verbose", "-v", action="store_true")


def _add_climate_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--start-year", default=str(2010), metavar="YEAR")
    p.add_argument("--end-year",   default=str(2023), metavar="YEAR")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="thermalcomfort",
        description="Perceived thermal comfort visualisation system",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # ── show ──────────────────────────────────────────────────────────
    p_show = sub.add_parser("show", help="Plot time-series for one location")
    p_show.add_argument("location", help="'Name:lat,lon' or 'lat,lon' or 'NameInDict'")
    _add_common(p_show)
    p_show.add_argument("--no-display", action="store_true")

    # ── compare ───────────────────────────────────────────────────────
    p_cmp = sub.add_parser("compare", help="Compare multiple locations")
    p_cmp.add_argument("locations", nargs="+", help="'Name:lat,lon' or 'lat,lon' or 'NameInDict' …")
    _add_common(p_cmp)
    p_cmp.add_argument(
        "--variable",
        default="utci",
        choices=COMMON_VARIABLE_CHOICES,
        help="Variable to compare",
    )
    p_cmp.add_argument("--hour", default=None,
                       help="Print table for this UTC hour (0-23)")

    # ── summary ───────────────────────────────────────────────────────
    p_sum = sub.add_parser("summary", help="UTCI distribution for a period")
    p_sum.add_argument("location", help="'Name:lat,lon' or 'lat,lon' or 'NameInDict'")
    _add_common(p_sum)

    # ── climate ───────────────────────────────────────────────────────
    p_cli = sub.add_parser("climate", help="Climatological monthly profile")
    p_cli.add_argument("location", help="'Name:lat,lon' or 'lat,lon' or 'NameInDict'")
    _add_common(p_cli, dates=False)
    _add_climate_args(p_cli)
    p_cli.add_argument("--month", default=None, metavar="1-12",
                       help="If given, plot hourly profile for that month")

    # ── rank ──────────────────────────────────────────────────────────
    p_rank = sub.add_parser("rank", help="Rank locations by comfort")
    p_rank.add_argument("locations", nargs="+", help="'Name:lat,lon' or 'lat,lon' or 'NameInDict' …")
    _add_common(p_rank, dates=False)
    _add_climate_args(p_rank)
    p_rank.add_argument("--month", default=None, metavar="1-12")

    # ── map ───────────────────────────────────────────────────────────
    p_map = sub.add_parser("map", help="Interactive/static comfort map")
    p_map.add_argument("locations", nargs="+", help="'Name:lat,lon' or 'lat,lon' or 'NameInDict' …")
    p_map.add_argument("--datetime", default=None, metavar="DATETIME",
                       help="UTC datetime to display (default: now)")
    _add_common(p_map, dates=False)
    p_map.add_argument(
        "--variable",
        default="utci",
        choices=MAP_VARIABLE_CHOICES,
        help="Variable shown on map markers",
    )
    p_map.add_argument("--static", action="store_true",
                       help="Static matplotlib map instead of interactive HTML")

    # ── calc ──────────────────────────────────────────────────────────
    p_calc = sub.add_parser(
        "calc",
        help="Calculate comfort indices from direct meteorological parameters (no database)",
    )
    p_calc.add_argument("--temp", "-T", type=float, required=True, metavar="°C",
                        help="Air temperature (°C)")
    p_calc.add_argument("--rh",   "-H", type=float, required=True, metavar="%",
                        help="Relative humidity (%%)")
    p_calc.add_argument("--wind", "-W", type=float, required=True, metavar="m/s",
                        help="Wind speed at 10 m height (m/s)")
    p_calc.add_argument("--mrt",  type=float, default=None, metavar="°C",
                        help="Mean Radiant Temperature (°C). "
                             "Defaults to air temperature (shade assumption).")
    p_calc.add_argument("--solar", type=float, default=None, metavar="W/m²",
                        help="Direct Normal Irradiance (W/m²) — alternative way to estimate MRT.")
    p_calc.add_argument("--solar-elevation", type=float, default=45.0, metavar="deg",
                        help="Solar elevation angle in degrees, used with --solar (default: 45).")
    p_calc.add_argument("--activity", default="walking",
                        choices=["resting", "seated", "standing", "walking",
                                 "walking_fast", "hiking", "cycling"],
                        help="Activity level (default: walking)")
    p_calc.add_argument("--sun", type=float, default=0.5, metavar="0-1",
                        help="Sun exposure fraction 0=shade … 1=full sun (default: 0.5)")

    # ── forecast ──────────────────────────────────────────────────────
    p_fcast = sub.add_parser("forecast", help="Forecast vs actual comparison")
    p_fcast.add_argument("location", help="'Name:lat,lon' or 'lat,lon' or 'NameInDict'")
    _add_common(p_fcast)
    p_fcast.add_argument(
        "--variable",
        default="utci",
        choices=COMMON_VARIABLE_CHOICES,
        help="Variable for forecast-vs-actual comparison",
    )

    # ── locations ─────────────────────────────────────────────────────
    sub.add_parser("locations", help="Print predefined known locations")

    args = parser.parse_args()

    # Set default datetime for map command
    if args.cmd == "map" and args.datetime is None:
        args.datetime = pd.Timestamp.now("UTC").floor("h").isoformat()

    dispatch = {
        "show":     cmd_show,
        "compare":  cmd_compare,
        "summary":  cmd_summary,
        "climate":  cmd_climate,
        "rank":     cmd_rank,
        "map":      cmd_map,
        "calc":     cmd_calc,
        "forecast": cmd_forecast,
        "locations": cmd_locations,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
