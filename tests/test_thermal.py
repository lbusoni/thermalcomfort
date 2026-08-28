#!/usr/bin/env python3

"""
Thermal comfort diagnostic using ERA5.

Calculates:
    - air temperature
    - dew point
    - relative humidity
    - wind speed
    - solar elevation
    - GHI
    - direct solar radiation
    - diffuse solar radiation
    - MRT
    - UTCI

The radiation treatment is:

    ERA5 ssrd [J/m²]
        -> GHI [W/m²]

    ERA5 fdir [J/m²]
        -> direct horizontal radiation [W/m²]
        -> DNI [W/m²]

    GHI - direct_horizontal
        -> diffuse horizontal radiation [W/m²]

The direct solar contribution to MRT is then calculated with
pythermalcomfort.solar_gain().

This is a diagnostic script: the intermediate radiation quantities
are deliberately printed so that the calculation can be validated
against ERA5 and ThermalTrace.
"""


# ============================================================
# IMPORTS
# ============================================================

import numpy as np
import pandas as pd
import xarray as xr
import pvlib

from pythermalcomfort.models import solar_gain, utci
from pythermalcomfort.utilities import v_relative


# ============================================================
# CONFIGURATION
# ============================================================

LAT = 43.76
LON = 11.25

INSTANT_FILE = "era5_extract/data_stream-oper_stepType-instant.nc"
RADIATION_FILE = "era5_extract/data_stream-oper_stepType-accum.nc"

OUTPUT_FILE = "thermal_diagnostic.csv"

# Activity
MET = 1.7                 # walking

# Fraction of body exposed to direct sun
SUN_EXPOSURE = 0.5

# Posture
POSTURE = "standing"

# Short-wave absorptivity
ALPHA_SW = 0.7

# Long-wave emissivity
EPSILON_BODY = 0.97

SIGMA = 5.670374419e-8


# ============================================================
# HELPERS
# ============================================================

def relative_humidity_from_t_td(t_c, td_c):
    """
    Relative humidity from air temperature and dew point.

    Magnus approximation.
    """

    a = 17.625
    b = 243.04

    es = np.exp(
        a * t_c / (b + t_c)
    )

    e = np.exp(
        a * td_c / (b + td_c)
    )

    return 100.0 * e / es


def select_florence(ds):
    """
    Select the ERA5 grid point nearest Florence.
    """

    return ds.sel(
        latitude=LAT,
        longitude=LON,
        method="nearest",
    )


def accumulated_to_flux(x):
    """
    Convert hourly accumulated energy [J/m²]
    to mean flux [W/m²].

    1 W = 1 J/s

    One ERA5 hourly accumulation therefore corresponds to:

        flux = accumulation / 3600
    """

    return np.asarray(x, dtype=float) / 3600.0


# ============================================================
# READ ERA5
# ============================================================

print()
print("Lettura dati ERA5...")


era5 = xr.open_dataset(INSTANT_FILE)
rad = xr.open_dataset(RADIATION_FILE)


print()
print("=" * 70)
print("ERA5 INSTANTANEO")
print("=" * 70)

print(era5)

print()
print("Variabili:")

for name in era5.data_vars:
    print("   ", name)


print()
print("=" * 70)
print("ERA5 RADIAZIONE")
print("=" * 70)

print(rad)

print()
print("Variabili:")

for name in rad.data_vars:
    print("   ", name)


# ============================================================
# SELECT GRID POINT
# ============================================================

era5_fi = select_florence(era5)
rad_fi = select_florence(rad)


print()
print("=" * 70)
print("PUNTO ERA5 UTILIZZATO")
print("=" * 70)

print(
    "latitude :",
    float(era5_fi.latitude.values)
)

print(
    "longitude:",
    float(era5_fi.longitude.values)
)


# ============================================================
# TIME
# ============================================================

time = pd.DatetimeIndex(
    era5_fi.valid_time.values
)

print()
print("Numero campioni:", len(time))

print(
    "Da:",
    time[0],
    "a:",
    time[-1],
)


# ============================================================
# METEOROLOGICAL VARIABLES
# ============================================================

Ta = (
    era5_fi["t2m"].values.astype(float)
    - 273.15
)

Td = (
    era5_fi["d2m"].values.astype(float)
    - 273.15
)

u10 = era5_fi["u10"].values.astype(float)

v10 = era5_fi["v10"].values.astype(float)


wind = np.sqrt(
    u10**2 + v10**2
)


RH = relative_humidity_from_t_td(
    Ta,
    Td,
)


# ============================================================
# SOLAR POSITION
# ============================================================

print()
print("Calcolo posizione del Sole...")


location = pvlib.location.Location(
    latitude=LAT,
    longitude=LON,
    tz="UTC",
)


solar_position = location.get_solarposition(
    time
)


solar_elevation = (
    solar_position["apparent_elevation"]
    .to_numpy(dtype=float)
)


# ============================================================
# RADIATION
# ============================================================

print()
print("=" * 70)
print("CALCOLO RADIAZIONE")
print("=" * 70)


# ------------------------------------------------------------
# ERA5 accumulated radiation
# ------------------------------------------------------------

ssrd_acc = rad_fi["ssrd"].values.astype(float)

fdir_acc = rad_fi["fdir"].values.astype(float)


# ------------------------------------------------------------
# Convert J/m² accumulated during the hour
# to W/m² average over the hour
# ------------------------------------------------------------

GHI = accumulated_to_flux(
    ssrd_acc
)

direct_horizontal = accumulated_to_flux(
    fdir_acc
)


# ------------------------------------------------------------
# Numerical sanity checks
# ------------------------------------------------------------

GHI = np.maximum(
    GHI,
    0.0,
)

direct_horizontal = np.maximum(
    direct_horizontal,
    0.0,
)


# Direct horizontal radiation cannot exceed GHI
direct_horizontal = np.minimum(
    direct_horizontal,
    GHI,
)


# ------------------------------------------------------------
# Diffuse horizontal radiation
# ------------------------------------------------------------

DHI = (
    GHI
    - direct_horizontal
)


DHI = np.maximum(
    DHI,
    0.0,
)


# ============================================================
# DNI
# ============================================================

"""
fdir is direct radiation on a horizontal surface.

For a horizontal surface:

    FDIR = DNI * sin(solar_elevation)

therefore:

    DNI = FDIR / sin(solar_elevation)

"""

DNI = np.zeros_like(
    direct_horizontal
)


daylight = (
    solar_elevation > 1.0
)


DNI[daylight] = (
    direct_horizontal[daylight]
    /
    np.sin(
        np.radians(
            solar_elevation[daylight]
        )
    )
)


# Protect against tiny numerical values
DNI = np.maximum(
    DNI,
    0.0,
)


# ============================================================
# PRINT RADIATION
# ============================================================

print()
print(
    f"{'time':19s}"
    f"{'elev':>8s}"
    f"{'GHI':>10s}"
    f"{'direct':>10s}"
    f"{'diffuse':>10s}"
    f"{'DNI':>10s}"
)

for i, t in enumerate(time):

    print(
        f"{str(t):19s}"
        f"{solar_elevation[i]:8.2f}"
        f"{GHI[i]:10.1f}"
        f"{direct_horizontal[i]:10.1f}"
        f"{DHI[i]:10.1f}"
        f"{DNI[i]:10.1f}"
    )


# ============================================================
# MRT
# ============================================================

print()
print("=" * 70)
print("CALCOLO MRT")
print("=" * 70)


# Start from air temperature.
MRT = Ta.copy()


solar_gain_mrt = np.zeros_like(
    Ta
)


diffuse_mrt = np.zeros_like(
    Ta
)


# ------------------------------------------------------------
# Direct solar contribution
# ------------------------------------------------------------

idx = np.where(
    daylight
    & (DNI > 0)
)[0]


if len(idx) > 0:

    sg = solar_gain(

        sol_altitude=
            solar_elevation[idx].tolist(),

        # We retain the same assumption as the previous script:
        # sun direction relative to body = 90 degrees.
        sharp=
            [90.0] * len(idx),

        sol_radiation_dir=
            DNI[idx].tolist(),

        sol_transmittance=
            [1.0] * len(idx),

        f_svv=
            [1.0] * len(idx),

        f_bes=
            [SUN_EXPOSURE] * len(idx),

        asw=ALPHA_SW,

        posture=POSTURE,

        round_output=False,
    )


    solar_gain_mrt[idx] = np.asarray(
        sg.delta_mrt,
        dtype=float,
    )


# ============================================================
# DIFFUSE SOLAR CONTRIBUTION
# ============================================================

"""
Approximate contribution of diffuse solar radiation.

For a horizontal isotropic sky:

    absorbed diffuse flux ≈ alpha * DHI / 2

Linearized Stefan-Boltzmann relation:

    ΔT ≈ q / (4 ε σ T³)

This is intentionally kept separate from the direct contribution
so that we can validate it independently.
"""


Ta_K = (
    Ta + 273.15
)


diffuse_mrt = (
    ALPHA_SW
    * 0.5
    * DHI
    /
    (
        4.0
        * EPSILON_BODY
        * SIGMA
        * Ta_K**3
    )
)


diffuse_mrt = np.nan_to_num(
    diffuse_mrt,
    nan=0.0,
    posinf=0.0,
    neginf=0.0,
)


# ============================================================
# TOTAL MRT
# ============================================================

# The direct-beam solar gain already carries an internal short-wave diffuse
# and reflected surrogate via pythermalcomfort.solar_gain(). We keep the
# separate diffuse estimate for inspection, but we do not add it again here.
MRT = (
    Ta
    + solar_gain_mrt
)


# ============================================================
# RELATIVE WIND SPEED
# ============================================================

wind_relative = np.asarray(
    v_relative(
        v=wind.tolist(),
        met=MET,
    ),
    dtype=float,
)


# ============================================================
# UTCI
# ============================================================

print()
print("Calcolo UTCI...")


utci_result = utci(

    tdb=Ta.tolist(),

    tr=MRT.tolist(),

    v=wind_relative.tolist(),

    rh=RH.tolist(),

    limit_inputs=False,

    round_output=False,
)


UTCI = np.asarray(
    utci_result.utci,
    dtype=float,
)


# ============================================================
# RESULT DATAFRAME
# ============================================================

result = pd.DataFrame(

    {

        "Ta_C": Ta,

        "Td_C": Td,

        "RH_%": RH,

        "wind_ms": wind,

        "wind_relative": wind_relative,

        "solar_elevation": solar_elevation,

        "GHI_Wm2": GHI,

        "direct_horizontal_Wm2":
            direct_horizontal,

        "DHI_Wm2": DHI,

        "DNI_Wm2": DNI,

        "solar_gain_mrt":
            solar_gain_mrt,

        "diffuse_mrt":
            diffuse_mrt,

        "mrt":
            MRT,

        "UTCI_C":
            UTCI,
    },

    index=time,
)


# ============================================================
# PRINT RESULTS
# ============================================================

print()
print("=" * 70)
print("RISULTATO")
print("=" * 70)

print(
    result.to_string(
        float_format=lambda x: f"{x:8.2f}"
    )
)


# ============================================================
# MAX UTCI
# ============================================================

imax = result["UTCI_C"].idxmax()


print()
print("=" * 70)
print("MASSIMO UTCI")
print("=" * 70)

print(
    result.loc[imax]
)


# ============================================================
# MAX MRT
# ============================================================

imrt = result["mrt"].idxmax()


print()
print("=" * 70)
print("MASSIMO MRT")
print("=" * 70)

print(
    result.loc[imrt]
)


# ============================================================
# SAVE
# ============================================================

result.to_csv(
    OUTPUT_FILE
)


print()
print("=" * 70)
print("FINE")
print("=" * 70)

print()
print(
    "Risultati salvati in:",
    OUTPUT_FILE,
)

print()


# ================================================================
# TEST SOLAR GAIN INDIPENDENTE
# ================================================================

from pythermalcomfort.models import solar_gain

print()
print("=" * 70)
print("TEST SOLAR GAIN")
print("=" * 70)

test_cases = [
    # altitude, sharp, DNI, f_bes
    (67.3,   0, 810, 0.5),
    (67.3,  45, 810, 0.5),
    (67.3,  90, 810, 0.5),

    (67.3,  90, 810, 0.25),
    (67.3,  90, 810, 0.75),
    (67.3,  90, 810, 1.00),

    (45.0,  90, 800, 0.5),
    (60.0,  90, 800, 0.5),
    (70.0,  90, 800, 0.5),
]

print()
print(
    f"{'alt':>6} {'sharp':>6} {'DNI':>7} {'f_bes':>7}"
    f" {'ERF':>10} {'delta_MRT':>12}"
)
print("-" * 65)

for alt, sharp, dni, fbes in test_cases:

    sg = solar_gain(
        sol_altitude=alt,
        sharp=sharp,
        sol_radiation_dir=dni,
        sol_transmittance=1.0,
        f_svv=1.0,
        f_bes=fbes,
        asw=0.7,
        posture="standing",
        floor_reflectance=0.6,
        round_output=False,
    )

    print(
        f"{alt:6.1f} {sharp:6.1f} {dni:7.1f} {fbes:7.2f}"
        f" {float(sg.erf):10.2f} {float(sg.delta_mrt):12.2f}"
    )
    
    
    
from pythermalcomfort.models import utci

Ta = 26.357
RH = 40.426
wind = 4.749

for MRT in [26.357, 40, 50.24, 60, 70, 85.27]:

    u = utci(
        tdb=Ta,
        tr=MRT,
        v=wind,
        rh=RH,
        limit_inputs=False,
        round_output=False,
    )

    print(f"MRT = {MRT:6.2f} °C   UTCI = {float(u.utci):6.2f} °C")
    
from pythermalcomfort.models import utci

Ta = 26.357
RH = 40.426
MRT = 50.24

for v in [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]:
    u = utci(
        tdb=Ta,
        tr=MRT,
        v=v,
        rh=RH,
        limit_inputs=False,
        round_output=False,
    )
    print(f"v = {v:4.1f} m/s   UTCI = {float(u.utci):6.2f} °C")