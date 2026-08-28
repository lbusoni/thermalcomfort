#!/usr/bin/env python3

"""
Download ERA5 hourly data needed for thermal-comfort calculations.

Downloads:

INSTANTANEOUS:
    t2m
    d2m
    u10
    v10

RADIATION / ACCUMULATED:
    ssrd
        Surface solar radiation downwards

    fdir
        Total sky direct solar radiation at surface

Both radiation variables are accumulated energy:
    J/m²

They must NOT be interpreted directly as W/m².
The conversion to hourly flux is done later.

Usage:
    python download_era5.py

Change DATE, LAT and LON below as required.
"""

# ===========
# CDSAPI rc
# url: https://cds.climate.copernicus.eu/api
# key: 534e4efa-d6a5-4d62-9dd6-c127a917cb81
# ============


# ============================================================
# CONFIGURATION
# ============================================================

DATE = "2026-06-10"

# Florence
LAT = 43.76
LON = 11.25

# ERA5 grid extraction area
#
# ERA5 resolution = 0.25°
#
# north, west, south, east
AREA = [
    LAT + 0.25,
    LON - 0.25,
    LAT - 0.25,
    LON + 0.25,
]

OUTPUT_DIR = "era5_extract"


# ============================================================
# IMPORT
# ============================================================

import os
import cdsapi


# ============================================================
# OUTPUT DIRECTORY
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True,
)


# ============================================================
# FILE NAMES
# ============================================================

instant_file = os.path.join(
    OUTPUT_DIR,
    "data_stream-oper_stepType-instant.nc",
)

radiation_file = os.path.join(
    OUTPUT_DIR,
    "data_stream-oper_stepType-accum.nc",
)


# ============================================================
# TIME
# ============================================================

TIMES = [
    f"{hour:02d}:00"
    for hour in range(24)
]


# ============================================================
# PRINT CONFIGURATION
# ============================================================

print()
print("=" * 70)
print("ERA5 DOWNLOAD")
print("=" * 70)

print()
print("Date:")
print("   ", DATE)

print()
print("Location:")
print("   latitude :", LAT)
print("   longitude:", LON)

print()
print("Area:")
print("   ", AREA)

print()


# ============================================================
# CDS CLIENT
# ============================================================

client = cdsapi.Client()


# ============================================================
# 1. INSTANTANEOUS DATA
# ============================================================

print("=" * 70)
print("1/2 - INSTANTANEOUS VARIABLES")
print("=" * 70)

instant_request = {

    "product_type": "reanalysis",

    "variable": [
        "2m_temperature",
        "2m_dewpoint_temperature",
        "10m_u_component_of_wind",
        "10m_v_component_of_wind",
    ],

    "year": DATE[0:4],
    "month": DATE[5:7],
    "day": DATE[8:10],

    "time": TIMES,

    "area": AREA,

    "data_format": "netcdf",

    "download_format": "unarchived",
}


print()
print("Variables:")
for v in instant_request["variable"]:
    print("   ", v)

print()
print("Downloading...")


client.retrieve(
    "reanalysis-era5-single-levels",
    instant_request,
    instant_file,
)


print()
print("Saved:")
print("   ", instant_file)


# ============================================================
# 2. ACCUMULATED RADIATION
# ============================================================

print()
print("=" * 70)
print("2/2 - ACCUMULATED RADIATION")
print("=" * 70)

radiation_request = {

    "product_type": "reanalysis",

    "variable": [

        # Global downward short-wave radiation
        "surface_solar_radiation_downwards",

        # Direct solar radiation
        "total_sky_direct_solar_radiation_at_surface",
    ],

    "year": DATE[0:4],
    "month": DATE[5:7],
    "day": DATE[8:10],

    "time": TIMES,

    "area": AREA,

    "data_format": "netcdf",

    "download_format": "unarchived",
}


print()
print("Variables:")

for v in radiation_request["variable"]:
    print("   ", v)

print()
print("Downloading...")


client.retrieve(
    "reanalysis-era5-single-levels",
    radiation_request,
    radiation_file,
)


print()
print("Saved:")
print("   ", radiation_file)


# ============================================================
# DONE
# ============================================================

print()
print("=" * 70)
print("DOWNLOAD COMPLETED")
print("=" * 70)

print()
print("Files:")
print()
print("   ", instant_file)
print("   ", radiation_file)
print()

print("You can inspect them with:")
print()
print("   xarray.open_dataset(...)")
print()
print("IMPORTANT:")
print("Radiation variables are accumulated J/m².")
print("Do not use them directly as W/m².")
print()