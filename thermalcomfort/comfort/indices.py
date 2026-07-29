"""Thermal comfort index calculations.

Primary index: UTCI (Universal Thermal Climate Index, Bröde et al. 2012).
  - Requires: air temperature, wind speed, Mean Radiant Temperature (MRT),
    relative humidity.
  - MRT is estimated from solar radiation components when available,
    otherwise falls back to air temperature (shade assumption).
  - Solar position (needed for direct-beam MRT contribution) is computed
    from latitude/longitude using pvlib.

Secondary indices (computed when data allows):
  - Heat Index (NOAA Rothfusz, valid for T > 27 °C and RH > 40 %)
  - Wind Chill Temperature (valid for T < 10 °C and wind > 1.3 m/s)
  - Wet-Bulb Globe Temperature (WBGT, simplified outdoor estimate)

Activity levels and sun exposure are explicit parameters.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
import pvlib

from pythermalcomfort.models import (
    heat_index_rothfusz,
    solar_gain,
    utci,
    wind_chill_temperature,
)
from pythermalcomfort.utilities import v_relative

# ---------------------------------------------------------------------------
# UTCI thermal stress categories (ISO TR 11079 / Bröde 2012)
# ---------------------------------------------------------------------------
UTCI_CATEGORIES = {
    "extreme cold stress": (-100, -40),
    "very strong cold stress": (-40, -27),
    "strong cold stress": (-27, -13),
    "moderate cold stress": (-13, 0),
    "slight cold stress": (0, 9),
    "no thermal stress": (9, 26),
    "moderate heat stress": (26, 32),
    "strong heat stress": (32, 38),
    "very strong heat stress": (38, 46),
    "extreme heat stress": (46, 200),
}

# Colour palette for UTCI categories (used by viz module)
UTCI_COLORS = {
    "extreme cold stress": "#053061",
    "very strong cold stress": "#2166ac",
    "strong cold stress": "#4393c3",
    "moderate cold stress": "#92c5de",
    "slight cold stress": "#d1e5f0",
    "no thermal stress": "#4dac26",
    "moderate heat stress": "#fee08b",
    "strong heat stress": "#f46d43",
    "very strong heat stress": "#d73027",
    "extreme heat stress": "#67001f",
}

# Metabolic rate presets [met]
ACTIVITY_MET = {
    "resting": 0.8,
    "seated": 1.0,
    "standing": 1.2,
    "walking": 1.7,    # ~1.2 m/s
    "walking_fast": 2.5,
    "hiking": 3.5,
    "cycling": 4.0,
}

# Minimum wind speed used in UTCI to avoid unrealistic calm-air extremes.
MIN_WIND_SPEED = 0.5  # m/s

# Stefan-Boltzmann constant
SIGMA = 5.67e-8  # W/m²/K⁴

# Short-wave absorptivity of human body (average skin + clothing)
ALPHA_SW = 0.7

# Long-wave emissivity of human body
EPSILON_BODY = 0.97


@dataclass
class ComfortParams:
    """Parameters controlling comfort index calculation.

    Attributes
    ----------
    activity : str | float
        Preset name (see ACTIVITY_MET) or a direct MET value.
    sun_exposure : float
        Fraction of body exposed to direct solar radiation, [0, 1].
        0 = full shade, 0.5 = typical outdoor (partial exposure), 1 = full sun.
    posture : str
        Body posture for solar gain calculation: 'standing' or 'sitting'.
    """

    activity: float | str = "walking"
    sun_exposure: float = 0.5
    posture: str = "standing"

    @property
    def met(self) -> float:
        if isinstance(self.activity, str):
            if self.activity not in ACTIVITY_MET:
                raise ValueError(
                    f"Unknown activity '{self.activity}'. "
                    f"Choose from: {list(ACTIVITY_MET)}"
                )
            return ACTIVITY_MET[self.activity]
        return float(self.activity)


def calculate_comfort(
    df: pd.DataFrame,
    lat: float,
    lon: float,
    params: Optional[ComfortParams] = None,
) -> pd.DataFrame:
    """Add thermal comfort indices to a weather DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Hourly weather data (UTC index) with at minimum the columns
        temperature_2m, relative_humidity_2m, wind_speed_10m.
    lat, lon : float
        Geographic coordinates, used for solar position calculation.
    params : ComfortParams, optional
        Activity level, sun exposure, posture. Defaults to ComfortParams().

    Returns
    -------
    pd.DataFrame
        Input DataFrame extended with columns:
        mrt, utci, utci_category, heat_index, wind_chill, wbgt_outdoor
    """
    if params is None:
        params = ComfortParams()

    result = df.copy()

    ta = result["temperature_2m"].to_numpy(dtype=float)
    rh = result["relative_humidity_2m"].to_numpy(dtype=float)
    ws = result["wind_speed_10m"].to_numpy(dtype=float)

    # Wind speed floored to avoid UTCI singularities.
    ws_clamped = np.where(np.isnan(ws), MIN_WIND_SPEED, np.maximum(ws, MIN_WIND_SPEED))

    # ------------------------------------------------------------------
    # Mean Radiant Temperature (MRT)
    # ------------------------------------------------------------------
    mrt = _estimate_mrt(result, lat, lon, ta, params)
    result["mrt"] = mrt

    # ------------------------------------------------------------------
    # UTCI
    # ------------------------------------------------------------------
    # Adjust wind speed for body movement (v_relative uses 10 m wind)
    vr = v_relative(v=ws_clamped.tolist(), met=params.met)
    vr = np.array(vr, dtype=float)

    utci_result = utci(
        tdb=ta.tolist(),
        tr=mrt.tolist(),
        v=vr.tolist(),
        rh=rh.tolist(),
        limit_inputs=False,
        round_output=False,
    )
    utci_vals = np.array(utci_result.utci, dtype=float)
    result["utci"] = utci_vals
    result["utci_category"] = _utci_category(utci_vals)

    # ------------------------------------------------------------------
    # Heat Index (NOAA Rothfusz, meaningful only for hot/humid conditions)
    # ------------------------------------------------------------------
    result["heat_index"] = _heat_index(ta, rh)

    # ------------------------------------------------------------------
    # Wind Chill Temperature (meaningful only for cold/windy conditions)
    # ------------------------------------------------------------------
    result["wind_chill"] = _wind_chill(ta, ws)

    # ------------------------------------------------------------------
    # WBGT outdoor (simplified Liljegren approximation)
    # ------------------------------------------------------------------
    result["wbgt_outdoor"] = _wbgt_outdoor(ta, rh, mrt)

    return result


# ---------------------------------------------------------------------------
# MRT estimation
# ---------------------------------------------------------------------------

def _estimate_mrt(
    df: pd.DataFrame,
    lat: float,
    lon: float,
    ta: np.ndarray,
    params: ComfortParams,
) -> np.ndarray:
    """Estimate Mean Radiant Temperature from solar radiation data.

    When direct-normal irradiance and solar position are available the MRT
    includes the short-wave solar gain (delta_mrt from pythermalcomfort's
    solar_gain model).  When radiation data is absent, MRT defaults to ta
    (full-shade approximation).
    """
    mrt = ta.copy()

    dni = _get_col(df, "direct_normal_irradiance")
    if dni is None:
        return mrt  # No radiation data → shade approximation

    # Solar position (pvlib, vectorised over the UTC timestamps)
    solar_pos = _solar_position(df.index, lat, lon)
    elevation = solar_pos["apparent_elevation"].to_numpy(dtype=float)
    # Only daylight hours with positive solar elevation
    day_mask = (elevation > 0) & ~np.isnan(dni) & (dni > 0)

    if not np.any(day_mask):
        return mrt

    # solar_gain expects scalar or list inputs; process daylight hours only
    idx = np.where(day_mask)[0]
    sol_alt = elevation[idx].tolist()
    sol_dir = dni[idx].tolist()
    ta_day = ta[idx].tolist()

    sg = solar_gain(
        sol_altitude=sol_alt,
        # 90° = sun from the side (worst-case / conservative assumption)
        sharp=[90.0] * len(idx),
        sol_radiation_dir=sol_dir,
        sol_transmittance=[1.0] * len(idx),   # fully outdoors
        f_svv=[1.0] * len(idx),               # open sky
        f_bes=[params.sun_exposure] * len(idx),
        asw=ALPHA_SW,
        posture=params.posture,
        round_output=False,
    )
    delta = np.array(sg.delta_mrt, dtype=float)

    # Add diffuse-sky contribution (half-sphere, fraction not blocked by sun)
    diff = _get_col(df, "diffuse_radiation")
    if diff is not None:
        diff_day = diff[idx]
        # Simplified diffuse MRT increment (ASHRAE / ISO 7933 approach)
        ta_k = ta[idx] + 273.15
        diff_delta = (
            ALPHA_SW * 0.5 * diff_day / (4.0 * EPSILON_BODY * SIGMA * ta_k**3)
        )
        delta = delta + np.nan_to_num(diff_delta, nan=0.0)

    mrt[idx] = ta[idx] + delta
    return mrt


def _solar_position(index: pd.DatetimeIndex, lat: float, lon: float) -> pd.DataFrame:
    loc = pvlib.location.Location(latitude=lat, longitude=lon, tz="UTC")
    return loc.get_solarposition(index)


def _get_col(df: pd.DataFrame, col: str) -> Optional[np.ndarray]:
    if col in df.columns:
        arr = df[col].to_numpy(dtype=float)
        if not np.all(np.isnan(arr)):
            return arr
    return None


# ---------------------------------------------------------------------------
# Secondary indices
# ---------------------------------------------------------------------------

def _heat_index(ta: np.ndarray, rh: np.ndarray) -> np.ndarray:
    """NOAA Rothfusz heat index; NaN outside applicability range."""
    result = np.full_like(ta, np.nan)
    mask = (ta >= 27.0) & (rh >= 40.0)
    if np.any(mask):
        hi = heat_index_rothfusz(
            tdb=ta[mask].tolist(),
            rh=rh[mask].tolist(),
            round_output=False,
        )
        result[mask] = np.array(hi.hi, dtype=float)
    return result


def _wind_chill(ta: np.ndarray, ws: np.ndarray) -> np.ndarray:
    """NWS Wind Chill Temperature; NaN outside applicability range."""
    result = np.full_like(ta, np.nan)
    # Valid for T ≤ 10 °C and wind > 1.3 m/s (4.8 km/h)
    mask = (ta <= 10.0) & (ws >= 1.3)
    if np.any(mask):
        wct = wind_chill_temperature(
            tdb=ta[mask].tolist(),
            v=ws[mask].tolist(),
            round_output=False,
        )
        result[mask] = np.array(wct.wct, dtype=float)
    return result


def _wbgt_outdoor(ta: np.ndarray, rh: np.ndarray, mrt: np.ndarray) -> np.ndarray:
    """Simplified outdoor WBGT (Liljegren et al. 2008 approximation).

    WBGT ≈ 0.7 * Twb + 0.2 * Tg + 0.1 * Ta
    where Tg (globe) ≈ MRT and Twb is the natural wet-bulb temperature.
    Twb is estimated via the Stull (2011) formula.
    """
    twb = _wet_bulb_stull(ta, rh)
    return 0.7 * twb + 0.2 * mrt + 0.1 * ta


def _wet_bulb_stull(ta: np.ndarray, rh: np.ndarray) -> np.ndarray:
    """Stull (2011) wet-bulb approximation, accurate to ±0.35 °C for
    -20 < Ta < 50 °C and 5 < RH < 99 %."""
    rh_c = np.clip(rh, 5.0, 99.0)
    return (
        ta * np.arctan(0.151977 * (rh_c + 8.313659) ** 0.5)
        + np.arctan(ta + rh_c)
        - np.arctan(rh_c - 1.676331)
        + 0.00391838 * rh_c**1.5 * np.arctan(0.023101 * rh_c)
        - 4.686035
    )


def _utci_category(utci_vals: np.ndarray) -> np.ndarray:
    categories = np.full(utci_vals.shape, "unknown", dtype=object)
    for label, (lo, hi) in UTCI_CATEGORIES.items():
        mask = (utci_vals >= lo) & (utci_vals < hi) & ~np.isnan(utci_vals)
        categories[mask] = label
    categories[np.isnan(utci_vals)] = "n/a"
    return categories
