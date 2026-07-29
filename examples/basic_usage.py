"""Basic usage: fetch and plot thermal comfort for a single location.

Run with:
    python examples/basic_usage.py
"""

import logging

from thermalcomfort import ComfortParams, Location, ThermalComfortSystem

# Enable info-level logging to see cache/fetch activity
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

tcs = ThermalComfortSystem()

# ----- Define location -----
florence = Location(lat=43.7696, lon=11.2558, name="Firenze")

# ----- Define comfort scenario -----
# Walking slowly in partial sun (typical city stroll)
params = ComfortParams(activity="walking", sun_exposure=0.5)

# ----- Fetch data (cached after first run) -----
df = tcs.get(florence, start="2024-07-01", end="2024-07-31 23:00", params=params)

print(df[["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "utci", "utci_category"]].tail(24))

# ----- Plot -----
tcs.plot(df, title="Firenze — Luglio 2024", local_tz="Europe/Rome")

# ----- UTCI distribution summary -----
tcs.plot_summary(df, label="Firenze Luglio 2024")
