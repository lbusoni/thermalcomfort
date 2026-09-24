"""Multi-location comparison example.

Answers questions like:
  "Ieri alle 19 si stava meglio a Firenze o a Livorno?"
  "Come mi sentirò domani a Borgo San Lorenzo rispetto a oggi a Firenze?"

Run with:
    python examples/compare_locations.py
"""

import logging

import pandas as pd

from thermalcomfort import ComfortParams, Location, ThermalComfortSystem

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

tcs = ThermalComfortSystem()

# ── Locations ──────────────────────────────────────────────────────────────
florence    = Location(lat=43.7696, lon=11.2558,  name="Firenze")
livorno     = Location(lat=43.5485, lon=10.3106,  name="Livorno")
borgo       = Location(lat=43.9543, lon=11.3882,  name="Borgo San Lorenzo")

# ── Scenario ───────────────────────────────────────────────────────────────
params = ComfortParams(sun_exposure=0.5, surface_type="asphalt")

# ── Example 1: "ieri alle 19 Firenze vs Livorno" ───────────────────────────
yesterday = (pd.Timestamp.now("UTC") - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
df_fi = tcs.get(florence, yesterday, yesterday + " 23:00", params=params)
df_li = tcs.get(livorno,  yesterday, yesterday + " 23:00", params=params)

hour_19_fi = df_fi.loc[df_fi.index.hour == 19]
hour_19_li = df_li.loc[df_li.index.hour == 19]

print(f"\n=== Ieri alle 19:00 UTC ===")
print(f"  Firenze  — UTCI: {hour_19_fi['utci'].mean():.1f} °C  ({hour_19_fi['utci_category'].iloc[0]})")
print(f"  Livorno  — UTCI: {hour_19_li['utci'].mean():.1f} °C  ({hour_19_li['utci_category'].iloc[0]})")

tcs.compare(
    [florence, livorno],
    start=yesterday,
    end=yesterday + " 23:00",
    variable="utci",
    params=params,
    local_tz="Europe/Rome",
)

# ── Example 2: today Firenze vs tomorrow Borgo San Lorenzo ─────────────────
today      = pd.Timestamp.now("UTC").strftime("%Y-%m-%d")
tomorrow   = (pd.Timestamp.now("UTC") + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

df_today_fi   = tcs.get(florence, today, today + " 23:00", params=params)
df_tom_borgo  = tcs.get(borgo, tomorrow, tomorrow + " 23:00", params=params)

hour_17_fi    = df_today_fi.loc[df_today_fi.index.hour == 15]   # 15 UTC ≈ 17 local
hour_13_borgo = df_tom_borgo.loc[df_tom_borgo.index.hour == 11] # 11 UTC ≈ 13 local

print(f"\n=== Oggi 17:00 locale (Firenze) vs Domani 13:00 locale (Borgo) ===")
if not hour_17_fi.empty:
    print(f"  Firenze oggi 17h  — UTCI: {hour_17_fi['utci'].iloc[0]:.1f} °C  ({hour_17_fi['utci_category'].iloc[0]})")
if not hour_13_borgo.empty:
    print(f"  Borgo domani 13h  — UTCI: {hour_13_borgo['utci'].iloc[0]:.1f} °C  ({hour_13_borgo['utci_category'].iloc[0]})")

# ── Example 3: best city in July (last year) ───────────────────────────────
last_year = pd.Timestamp.now("UTC").year - 1
cities = [
    Location(lat=48.8566, lon=2.3522,   name="Parigi"),
    Location(lat=41.9028, lon=12.4964,  name="Roma"),
    Location(lat=43.7696, lon=11.2558,  name="Firenze"),
    Location(lat=52.5200, lon=13.4050,  name="Berlino"),
    Location(lat=37.9838, lon=23.7275,  name="Atene"),
    Location(lat=39.9334, lon=32.8597,  name="Ankara"),
]

print(f"\n=== Miglior città per luglio {last_year} (UTCI medio diurno) ===")
results = []
for city in cities:
    try:
        df = tcs.get(city, f"{last_year}-07-01", f"{last_year}-07-31 23:00", params=params)
        # Daytime hours only (06-21 UTC)
        daytime = df[(df.index.hour >= 6) & (df.index.hour <= 21)]
        mean_utci = daytime["utci"].mean()
        no_stress = (daytime["utci_category"] == "no thermal stress").mean()
        results.append((city.name, mean_utci, no_stress))
    except Exception as e:
        print(f"  {city.name}: error — {e}")

results.sort(key=lambda x: abs(x[1] - 17))  # closest to ideal ~17 °C UTCI
for name, mu, ns in results:
    print(f"  {name:15s}  UTCI medio = {mu:.1f} °C   no-stress = {ns:.0%}")
