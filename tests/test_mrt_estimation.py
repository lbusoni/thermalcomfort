"""Regression tests for the outdoor MRT radiative-flux-balance model.

MRT is derived from a full short-wave + long-wave flux balance (Thorsson et
al. 2007 / VDI 3787 style, see thermalcomfort/comfort/mrt.py), not from
pythermalcomfort's solar_gain() — an ASHRAE 55 *indoor* model (person near a
sunlit window). Applied outdoors with its default indoor floor reflectance
(0.6, meant for a room floor, not ground albedo), that additive model used
to push MRT to ~85 degC at summer noon; this suite guards against that
regressing.
"""

import pandas as pd
import pytest

from thermalcomfort.comfort.indices import ComfortParams, calculate_comfort
from thermalcomfort.comfort.mrt import calculate_outdoor_mrt


LAT = 43.75
LON = 11.25


def _make_row(**overrides):
    base = {
        "temperature_2m": 26.357,
        "relative_humidity_2m": 40.426,
        "wind_speed_10m": 4.749,
        "direct_normal_irradiance": float("nan"),
        "diffuse_radiation": float("nan"),
        "shortwave_radiation": float("nan"),
        "cloud_cover": float("nan"),
    }
    base.update(overrides)
    return pd.DataFrame(
        [base],
        index=pd.DatetimeIndex(["2026-06-10T12:00:00Z"]),
    )


def test_mrt_cools_below_ta_at_night_under_a_clear_sky():
    # No radiation and no cloud data at all -> clear-sky assumption. A body
    # radiating to a clear night sky loses more long-wave than it receives
    # back (sky emissivity < 1), so MRT must sit below Ta, not equal to it
    # as the old "shade -> MRT = Ta" fallback assumed.
    df = _make_row()
    result = calculate_comfort(df, lat=LAT, lon=LON, params=ComfortParams())

    mrt = float(result["mrt"].iloc[0])
    ta = float(df["temperature_2m"].iloc[0])
    assert mrt < ta - 1.0


def test_full_cloud_cover_is_closer_to_ta_than_clear_sky():
    clear = _make_row(cloud_cover=0.0)
    overcast = _make_row(cloud_cover=100.0)

    ta = float(clear["temperature_2m"].iloc[0])
    mrt_clear = float(
        calculate_comfort(clear, lat=LAT, lon=LON, params=ComfortParams())["mrt"].iloc[0]
    )
    mrt_overcast = float(
        calculate_comfort(overcast, lat=LAT, lon=LON, params=ComfortParams())["mrt"].iloc[0]
    )

    assert abs(mrt_overcast - ta) < abs(mrt_clear - ta)


def test_full_sun_summer_noon_mrt_is_physically_plausible():
    # Regression guard for the ~85 degC bug: the old default
    # floor_reflectance=0.6 from solar_gain() (an indoor ASHRAE value used
    # as if it were outdoor ground albedo) used to blow MRT up to ~52 degC
    # above Ta. A realistic radiative balance keeps it in a plausible
    # full-sun range instead.
    df = _make_row(
        temperature_2m=30.0,
        direct_normal_irradiance=850.0,
        diffuse_radiation=120.0,
        shortwave_radiation=900.0,
        cloud_cover=0.0,
    )
    result = calculate_comfort(df, lat=LAT, lon=LON, params=ComfortParams(sun_exposure=0.5))

    mrt = float(result["mrt"].iloc[0])
    assert 40.0 < mrt < 65.0


def test_mrt_increases_with_sun_exposure():
    df = _make_row(
        temperature_2m=30.0,
        direct_normal_irradiance=850.0,
        diffuse_radiation=120.0,
        shortwave_radiation=900.0,
        cloud_cover=0.0,
    )
    shaded = calculate_comfort(df, lat=LAT, lon=LON, params=ComfortParams(sun_exposure=0.0))
    full_sun = calculate_comfort(df, lat=LAT, lon=LON, params=ComfortParams(sun_exposure=1.0))

    assert float(full_sun["mrt"].iloc[0]) > float(shaded["mrt"].iloc[0])


def test_asphalt_is_hotter_than_grass_in_full_sun():
    df = _make_row(
        temperature_2m=30.0,
        direct_normal_irradiance=850.0,
        diffuse_radiation=120.0,
        shortwave_radiation=900.0,
        cloud_cover=0.0,
    )
    asphalt = calculate_comfort(df, lat=LAT, lon=LON, params=ComfortParams(surface_type="asphalt"))
    grass = calculate_comfort(df, lat=LAT, lon=LON, params=ComfortParams(surface_type="grass"))

    assert float(asphalt["mrt"].iloc[0]) > float(grass["mrt"].iloc[0])


def test_unknown_surface_type_raises():
    df = _make_row()
    with pytest.raises(ValueError):
        calculate_comfort(df, lat=LAT, lon=LON, params=ComfortParams(surface_type="marble"))


def test_utci_uses_raw_10m_wind():
    from pythermalcomfort.models import utci

    df = _make_row()
    result = calculate_comfort(df, lat=LAT, lon=LON, params=ComfortParams())

    expected = utci(
        tdb=float(df["temperature_2m"].iloc[0]),
        tr=float(result["mrt"].iloc[0]),
        v=float(df["wind_speed_10m"].iloc[0]),
        rh=float(df["relative_humidity_2m"].iloc[0]),
        limit_inputs=False,
        round_output=False,
    )

    assert abs(float(result["utci"].iloc[0]) - float(expected.utci)) < 1e-9


def test_calculate_outdoor_mrt_matches_calculate_comfort_wiring():
    # calculate_comfort must pass through the same columns/units
    # (cloud_cover as % -> fraction) that calculate_outdoor_mrt expects.
    import numpy as np

    df = _make_row(
        temperature_2m=30.0,
        direct_normal_irradiance=850.0,
        diffuse_radiation=120.0,
        shortwave_radiation=900.0,
        cloud_cover=25.0,
    )
    result = calculate_comfort(df, lat=LAT, lon=LON, params=ComfortParams(sun_exposure=0.5))

    import pvlib

    elevation = float(
        pvlib.location.Location(latitude=LAT, longitude=LON, tz="UTC")
        .get_solarposition(df.index)["apparent_elevation"]
        .iloc[0]
    )
    expected = calculate_outdoor_mrt(
        ta=np.array([30.0]),
        rh=np.array([float(df["relative_humidity_2m"].iloc[0])]),
        ghi=np.array([900.0]),
        dni=np.array([850.0]),
        dhi=np.array([120.0]),
        solar_elevation=np.array([elevation]),
        cloud_fraction=np.array([0.25]),
        sun_exposure=0.5,
        surface_type="asphalt",
    )[0]

    assert abs(float(result["mrt"].iloc[0]) - float(expected)) < 1e-6
