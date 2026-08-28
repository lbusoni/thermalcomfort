
"""
test_utci_copernicus.py

Confronto tra:
    1. UTCI ufficiale del dataset Copernicus derived-utci-historical
    2. UTCI calcolato localmente con pythermalcomfort

Dati:
    ERA5:
        era5_extract/data_stream-oper_stepType-instant.nc

    Copernicus UTCI:
        era5_extract/utci_firenze_20260610.nc

IMPORTANTE:
    Il dataset Copernicus UTCI contiene MRT e UTCI in Kelvin.
    Vengono convertiti in °C prima del confronto.

Per il confronto "standard":
    - Ta  = ERA5 2 m temperature
    - RH  = calcolata da T2m e Td2m
    - V   = ERA5 wind speed 10 m
    - MRT = MRT fornita da Copernicus
    - nessun v_relative()
    - nessun MET
    - nessun solar_gain()
"""

import os
import numpy as np
import pandas as pd
import xarray as xr

from pythermalcomfort.models import utci


# ======================================================================
# CONFIGURAZIONE
# ======================================================================

ERA5_FILE = "era5_extract/data_stream-oper_stepType-instant.nc"
UTCI_FILE = "era5_extract/utci_firenze_20260610.nc"

OUTPUT_FILE = "utci_copernicus_comparison.csv"

# Punto ERA5.
# Il file contiene 43.75 / 11.25, che è il punto più vicino a Firenze
# utilizzato anche per il dataset UTCI.
LAT = 43.75
LON = 11.25


# ======================================================================
# FUNZIONI
# ======================================================================

def calculate_relative_humidity(t_c, td_c):
    """
    Calcola RH [%] da temperatura dell'aria e dew point.

    Formula Magnus.
    """

    a = 17.625
    b = 243.04

    gamma_t = (a * t_c) / (b + t_c)
    gamma_td = (a * td_c) / (b + td_c)

    rh = 100.0 * np.exp(gamma_td - gamma_t)

    return np.clip(rh, 0.0, 100.0)


def find_nearest_point(ds, lat, lon):
    """
    Seleziona il punto di griglia più vicino.
    """

    return ds.sel(
        latitude=lat,
        longitude=lon,
        method="nearest",
    )


# ======================================================================
# LETTURA ERA5
# ======================================================================

print()
print("=" * 70)
print("LETTURA ERA5")
print("=" * 70)
print()

if not os.path.exists(ERA5_FILE):
    raise FileNotFoundError(
        f"File ERA5 non trovato:\n    {ERA5_FILE}"
    )

print(f"File:\n  {ERA5_FILE}")

era5_ds = xr.open_dataset(ERA5_FILE)

print()
print("Variabili ERA5:")
for name in era5_ds.data_vars:
    print(f"  {name}")

print()

era5_point = find_nearest_point(era5_ds, LAT, LON)

actual_lat = float(era5_point.latitude.values)
actual_lon = float(era5_point.longitude.values)

print("Punto ERA5 utilizzato:")
print(f"  latitude  = {actual_lat}")
print(f"  longitude = {actual_lon}")

# Timestamp
time = pd.DatetimeIndex(
    era5_point["valid_time"].values
)

print()
print(f"Numero campioni: {len(time)}")
print(f"Da: {time[0]}")
print(f"A : {time[-1]}")


# ======================================================================
# ESTRAZIONE ERA5
# ======================================================================

t2m_k = era5_point["t2m"].values.astype(float)
d2m_k = era5_point["d2m"].values.astype(float)

u10 = era5_point["u10"].values.astype(float)
v10 = era5_point["v10"].values.astype(float)

# Kelvin -> Celsius
ta = t2m_k - 273.15
td = d2m_k - 273.15

# Wind speed
wind = np.sqrt(u10**2 + v10**2)

# Relative humidity
rh = calculate_relative_humidity(ta, td)


# ======================================================================
# LETTURA UTCI COPERNICUS
# ======================================================================

print()
print("=" * 70)
print("LETTURA UTCI COPERNICUS")
print("=" * 70)
print()

if not os.path.exists(UTCI_FILE):
    raise FileNotFoundError(
        f"File UTCI Copernicus non trovato:\n    {UTCI_FILE}"
    )

print(f"File:\n  {UTCI_FILE}")

utci_ds = xr.open_dataset(UTCI_FILE)

print()
print("Dimensioni:")
print(utci_ds.sizes)

print()
print("Coordinate:")

for name in utci_ds.coords:
    coord = utci_ds[name]

    print(
        f"  {name}: "
        f"dims={coord.dims}, "
        f"shape={coord.shape}"
    )

print()
print("Variabili:")

for name in utci_ds.data_vars:
    print(f"  {name}")


# ======================================================================
# ESTRAZIONE UTCI COPERNICUS
# ======================================================================

if "utci" not in utci_ds:
    raise KeyError(
        "Nel file Copernicus non trovo la variabile 'utci'."
    )

if "mrt" not in utci_ds:
    raise KeyError(
        "Nel file Copernicus non trovo la variabile 'mrt'."
    )

# Le coordinate latitude e longitude nel file UTCI sono scalari,
# quindi NON usiamo .sel(latitude=..., longitude=...).

utci_time = pd.DatetimeIndex(
    utci_ds["valid_time"].values
)

# Valori ORIGINALI Copernicus
mrt_k = utci_ds["mrt"].values.astype(float)
utci_k = utci_ds["utci"].values.astype(float)

# --------------------------------------------------------------
# IMPORTANTISSIMO:
#
# Copernicus fornisce temperature in Kelvin.
#
# 323.391 K = 50.241 °C
# 302.741 K = 29.591 °C
#
# Convertiamo tutto in °C.
# --------------------------------------------------------------

mrt_copernicus = mrt_k - 273.15
utci_copernicus = utci_k - 273.15


# ======================================================================
# CONTROLLO COORDINATE / TEMPI
# ======================================================================

print()
print("Coordinate del dataset UTCI:")

if "latitude" in utci_ds.coords:
    print(
        f"  latitude  = "
        f"{float(utci_ds.latitude.values):.4f}"
    )

if "longitude" in utci_ds.coords:
    print(
        f"  longitude = "
        f"{float(utci_ds.longitude.values):.4f}"
    )

print()
print("Numero campioni UTCI:", len(utci_time))
print(f"Da: {utci_time[0]}")
print(f"A : {utci_time[-1]}")


# ======================================================================
# VERIFICA ALLINEAMENTO TEMPORALE
# ======================================================================

if len(time) != len(utci_time):
    raise ValueError(
        "ERA5 e UTCI Copernicus hanno un numero diverso "
        "di campioni."
    )

if not np.array_equal(time.values, utci_time.values):
    print()
    print("ATTENZIONE: timestamp non perfettamente identici.")
    print("Verrà comunque effettuato il confronto per posizione.")

    # In questo caso costruiamo comunque una tabella coerente
    # usando l'indice temporale ERA5.
else:
    print()
    print("Timestamp ERA5 e Copernicus perfettamente allineati.")


# ======================================================================
# CONTROLLO UNITÀ
# ======================================================================

print()
print("=" * 70)
print("CONTROLLO UNITÀ")
print("=" * 70)
print()

print(
    f"MRT Copernicus originale : "
    f"{np.nanmin(mrt_k):.3f} ... {np.nanmax(mrt_k):.3f} K"
)

print(
    f"MRT Copernicus convertito: "
    f"{np.nanmin(mrt_copernicus):.3f} ... "
    f"{np.nanmax(mrt_copernicus):.3f} °C"
)

print()

print(
    f"UTCI Copernicus originale : "
    f"{np.nanmin(utci_k):.3f} ... {np.nanmax(utci_k):.3f} K"
)

print(
    f"UTCI Copernicus convertito: "
    f"{np.nanmin(utci_copernicus):.3f} ... "
    f"{np.nanmax(utci_copernicus):.3f} °C"
)


# ======================================================================
# CALCOLO UTCI
# ======================================================================

print()
print("=" * 70)
print("CALCOLO UTCI")
print("=" * 70)
print()

print("Usiamo direttamente:")
print("  Ta  = ERA5")
print("  RH  = ERA5")
print("  V   = ERA5")
print("  MRT = Copernicus")
print()
print("Nessun v_relative()")
print("Nessun MET")
print("Nessun solar_gain()")
print()

# pythermalcomfort vuole:
#
#   tdb = °C
#   tr  = °C
#   v   = m/s
#   rh  = %

utci_result = utci(
    tdb=ta.tolist(),
    tr=mrt_copernicus.tolist(),
    v=wind.tolist(),
    rh=rh.tolist(),
    limit_inputs=False,
    round_output=False,
)

utci_calcolato = np.asarray(
    utci_result.utci,
    dtype=float
)


# ======================================================================
# COSTRUZIONE TABELLA
# ======================================================================

comparison = pd.DataFrame(
    {
        "Ta_C": ta,
        "Td_C": td,
        "RH_%": rh,
        "wind_ms": wind,
        "MRT_C_Copernicus": mrt_copernicus,
        "UTCI_C_Copernicus": utci_copernicus,
        "UTCI_C_calcolato": utci_calcolato,
    },
    index=time,
)

comparison["Delta_UTCI_C"] = (
    comparison["UTCI_C_calcolato"]
    - comparison["UTCI_C_Copernicus"]
)


# ======================================================================
# OUTPUT
# ======================================================================

print()
print("=" * 70)
print("CONFRONTO UTCI COPERNICUS vs CALCOLATO")
print("=" * 70)
print()

print(
    comparison.to_string(
        float_format=lambda x: f"{x:8.3f}"
    )
)


# ======================================================================
# STATISTICHE
# ======================================================================

delta = comparison["Delta_UTCI_C"].to_numpy()

valid = np.isfinite(delta)

delta_valid = delta[valid]

if len(delta_valid) > 0:

    mae = np.mean(np.abs(delta_valid))

    rmse = np.sqrt(
        np.mean(delta_valid**2)
    )

    bias = np.mean(delta_valid)

    std = np.std(
        delta_valid,
        ddof=1,
    ) if len(delta_valid) > 1 else 0.0

    print()
    print("=" * 70)
    print("STATISTICHE")
    print("=" * 70)
    print()

    print(f"Numero campioni : {len(delta_valid)}")
    print(f"Bias medio      : {bias:.4f} °C")
    print(f"Dev. standard   : {std:.4f} °C")
    print(f"Min             : {np.min(delta_valid):.4f} °C")
    print(f"Max             : {np.max(delta_valid):.4f} °C")
    print(f"MAE             : {mae:.4f} °C")
    print(f"RMSE            : {rmse:.4f} °C")


# ======================================================================
# MASSIMO UTCI COPERNICUS
# ======================================================================

idx_max_cop = comparison[
    "UTCI_C_Copernicus"
].idxmax()

print()
print("=" * 70)
print("MASSIMO UTCI COPERNICUS")
print("=" * 70)
print()

print(
    comparison.loc[idx_max_cop].to_string(
        float_format=lambda x: f"{x:.4f}"
    )
)


# ======================================================================
# MASSIMO UTCI CALCOLATO
# ======================================================================

idx_max_calc = comparison[
    "UTCI_C_calcolato"
].idxmax()

print()
print("=" * 70)
print("MASSIMO UTCI CALCOLATO")
print("=" * 70)
print()

print(
    comparison.loc[idx_max_calc].to_string(
        float_format=lambda x: f"{x:.4f}"
    )
)


# ======================================================================
# CONTROLLO SPECIFICO DELLE 12:00
# ======================================================================

target_time = pd.Timestamp("2026-06-10 12:00:00")

if target_time in comparison.index:

    row = comparison.loc[target_time]

    print()
    print("=" * 70)
    print("CONTROLLO ORE 12:00")
    print("=" * 70)
    print()

    print(f"Ta                  = {row['Ta_C']:.3f} °C")
    print(f"RH                  = {row['RH_%']:.3f} %")
    print(f"vento               = {row['wind_ms']:.3f} m/s")
    print(
        f"MRT Copernicus      = "
        f"{row['MRT_C_Copernicus']:.3f} °C"
    )
    print(
        f"UTCI Copernicus     = "
        f"{row['UTCI_C_Copernicus']:.3f} °C"
    )
    print(
        f"UTCI calcolato      = "
        f"{row['UTCI_C_calcolato']:.3f} °C"
    )
    print(
        f"Differenza          = "
        f"{row['Delta_UTCI_C']:.3f} °C"
    )


# ======================================================================
# SALVATAGGIO
# ======================================================================

comparison.to_csv(
    OUTPUT_FILE,
    float_format="%.6f",
)

print()
print("=" * 70)
print("FINE")
print("=" * 70)
print()
print(
    f"Risultati salvati in: {OUTPUT_FILE}"
)

