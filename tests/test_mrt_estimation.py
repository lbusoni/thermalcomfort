"""Regression test for MRT estimation used by UTCI.

The goal is to keep the model aligned with the scientific interpretation of
UTCI inputs:
  - in shade, MRT should fall back to Ta;
  - with direct solar input, MRT should follow solar_gain() without adding a
    second diffuse term on top of it.
"""

import pandas as pd
import pvlib

from pythermalcomfort.models import solar_gain, utci

from thermalcomfort.comfort.indices import ComfortParams, calculate_comfort


LAT = 43.75
LON = 11.25


def _make_row(**overrides):
    base = {
        "temperature_2m": 26.357,
        "relative_humidity_2m": 40.426,
        "wind_speed_10m": 4.749,
        "direct_normal_irradiance": float("nan"),
        "diffuse_radiation": float("nan"),
    }
    base.update(overrides)
    return pd.DataFrame(
        [base],
        index=pd.DatetimeIndex(["2026-06-10T12:00:00Z"]),
    )


def test_mrt_falls_back_to_ta_without_radiation():
    df = _make_row()

    result = calculate_comfort(df, lat=LAT, lon=LON, params=ComfortParams())

    assert float(result["mrt"].iloc[0]) == float(df["temperature_2m"].iloc[0])


def test_mrt_matches_solar_gain_without_extra_diffuse_term():
    df = _make_row(
        direct_normal_irradiance=809.779024,
        diffuse_radiation=153.457778,
    )

    result = calculate_comfort(df, lat=LAT, lon=LON, params=ComfortParams())

    solar_pos_altitude = float(
        pvlib.location.Location(latitude=LAT, longitude=LON, tz="UTC")
        .get_solarposition(df.index)["apparent_elevation"]
        .iloc[0]
    )
    expected = solar_gain(
        sol_altitude=solar_pos_altitude,
        sharp=90.0,
        sol_radiation_dir=809.779024,
        sol_transmittance=1.0,
        f_svv=1.0,
        f_bes=0.5,
        asw=0.7,
        posture="standing",
        round_output=False,
    )

    expected_mrt = float(df["temperature_2m"].iloc[0]) + float(expected.delta_mrt)
    actual_mrt = float(result["mrt"].iloc[0])

    # The diffuse column is kept in the input, but it must not be added a
    # second time when direct-beam data are available.
    assert abs(actual_mrt - expected_mrt) < 1e-6


def test_utci_uses_raw_10m_wind():
    df = _make_row()
    result = calculate_comfort(df, lat=LAT, lon=LON, params=ComfortParams())

    expected = utci(
        tdb=float(df["temperature_2m"].iloc[0]),
        tr=float(df["temperature_2m"].iloc[0]),
        v=float(df["wind_speed_10m"].iloc[0]),
        rh=float(df["relative_humidity_2m"].iloc[0]),
        limit_inputs=False,
        round_output=False,
    )

    assert abs(float(result["utci"].iloc[0]) - float(expected.utci)) < 1e-9
