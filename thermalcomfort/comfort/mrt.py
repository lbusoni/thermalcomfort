"""Outdoor Mean Radiant Temperature (MRT) via a full radiative flux balance.

MRT is derived from the total short-wave + long-wave radiant flux absorbed
by a standing person, inverted through the Stefan-Boltzmann law — the
approach used in outdoor human biometeorology (Thorsson et al. 2007;
Kantor & Unger 2011; VDI 3787), rather than pythermalcomfort's
``solar_gain()``, which implements the ASHRAE 55 *indoor* model (a person
near a sunlit window) and additively raises Ta by a delta linearised for
near-room temperatures. Applied outdoors with its default indoor floor
reflectance (0.6, meant for a room floor, not ground albedo) that additive
model produced MRT values as high as ~85 degC at summer noon.

Radiative balance, following Thorsson et al. (2007):

    MRT = [ (S_abs + L_abs) / (epsilon_p * sigma) ] ** 0.25

- S_abs = alpha_sw * (S_dir + S_diff + S_ref)   [short-wave absorbed]
- L_abs = epsilon_p * (0.5 * L_down + 0.5 * L_up)   [long-wave absorbed]

Sky and ground are each weighted 0.5 (two-hemisphere simplification, no
detailed 3D view factors).
"""

from __future__ import annotations

from typing import Union

import numpy as np

ArrayLike = Union[float, np.ndarray]

SIGMA = 5.67e-8  # Stefan-Boltzmann constant, W/m^2/K^4
EPSILON_BODY = 0.97  # long-wave emissivity of clothed human body
EPSILON_GROUND = 0.95  # long-wave emissivity of typical ground surfaces
ALPHA_SW = 0.7  # short-wave absorptivity of human body (skin + clothing)

# Ground surface properties:
#   albedo      - short-wave reflectance, used for the reflected term S_ref.
#   heating_k   - empirical solar-heating coefficient [degC per W/m^2 of
#                 GHI] used to estimate ground surface temperature as
#                 Ta + heating_k * GHI. Order-of-magnitude approximation,
#                 not a calibrated fit against measured surface temperatures.
SURFACE_PROPERTIES = {
    "asphalt": {"albedo": 0.10, "heating_k": 0.025},
    "grass": {"albedo": 0.20, "heating_k": 0.005},
}

# Projected-area factor f_p of a standing person receiving direct-beam solar
# radiation from the side (SHARP = 90 deg — sun from the side, the fixed,
# conservative default geometry used throughout this package). Values are
# the standing/SHARP=90 column of the ASHRAE 55 (2020) Appendix C f_p table
# (Underwood & Ward 1966), the same empirical data pythermalcomfort's
# solar_gain() uses — reused here directly rather than re-deriving the
# closed-form Fanger polynomial, whose angle convention (altitude vs.
# zenith, degrees vs. radians) is inconsistently reported across sources.
_FP_ALTITUDES_DEG = np.array([0.0, 15.0, 30.0, 45.0, 60.0, 75.0, 90.0])
_FP_STANDING_SHARP90 = np.array([0.230, 0.230, 0.214, 0.180, 0.148, 0.108, 0.082])


def _projected_area_factor(solar_elevation_deg: np.ndarray) -> np.ndarray:
    elevation = np.clip(solar_elevation_deg, 0.0, 90.0)
    return np.interp(elevation, _FP_ALTITUDES_DEG, _FP_STANDING_SHARP90)


def _saturation_vapor_pressure_hpa(ta: np.ndarray) -> np.ndarray:
    """Magnus-type formula for saturation vapour pressure, hPa (Ta in degC)."""
    return 6.1078 * np.exp(17.27 * ta / (ta + 237.3))


def _sky_emissivity(
    ta: np.ndarray, rh: np.ndarray, cloud_fraction: np.ndarray
) -> np.ndarray:
    """Effective sky emissivity: Prata (1996) clear-sky model with a
    Crawford & Duchon (2001) cloud correction.

    Prata's precipitable-water proxy w [cm] is derived from screen-level
    vapour pressure e [hPa] and air temperature [K]:

        w = 46.5 * e / Ta_K
        epsilon_clear = 1 - (1 + w) * exp(-sqrt(1.2 + 3w))

    Clouds are treated as blackbody emitters weighted by cloud fraction N:

        epsilon_sky = epsilon_clear + N * (1 - epsilon_clear)
    """
    ta_k = ta + 273.15
    e_hpa = np.clip(rh, 0.0, 100.0) / 100.0 * _saturation_vapor_pressure_hpa(ta)
    w = 46.5 * (e_hpa / ta_k)
    epsilon_clear = 1.0 - (1.0 + w) * np.exp(-np.sqrt(1.2 + 3.0 * w))
    n = np.clip(cloud_fraction, 0.0, 1.0)
    return epsilon_clear + n * (1.0 - epsilon_clear)


def calculate_outdoor_mrt(
    ta: ArrayLike,
    rh: ArrayLike,
    ghi: ArrayLike,
    dni: ArrayLike,
    dhi: ArrayLike,
    solar_elevation: ArrayLike,
    cloud_fraction: ArrayLike,
    sun_exposure: float = 0.5,
    surface_type: str = "asphalt",
) -> np.ndarray:
    """Estimate outdoor Mean Radiant Temperature from a radiative flux balance.

    Parameters
    ----------
    ta : Air temperature, degC.
    rh : Relative humidity, % (0-100).
    ghi : Global horizontal irradiance, W/m^2. NaN treated as 0.
    dni : Direct normal irradiance, W/m^2. NaN treated as 0.
    dhi : Diffuse horizontal irradiance, W/m^2. NaN treated as 0.
    solar_elevation : Solar elevation angle, degrees (<=0 -> night, no
        direct-beam contribution).
    cloud_fraction : Cloud cover fraction, 0-1. NaN treated as 0 (clear sky).
    sun_exposure : Fraction of the body's direct-beam-facing surface that is
        actually in the sun (0 = full shade, 1 = full sun), [0, 1].
    surface_type : Ground surface under the person. See SURFACE_PROPERTIES
        for available options.

    Returns
    -------
    np.ndarray
        Mean Radiant Temperature, degC.
    """
    if surface_type not in SURFACE_PROPERTIES:
        raise ValueError(
            f"Unknown surface_type {surface_type!r}. "
            f"Choose from: {list(SURFACE_PROPERTIES)}"
        )
    albedo = SURFACE_PROPERTIES[surface_type]["albedo"]
    heating_k = SURFACE_PROPERTIES[surface_type]["heating_k"]

    ta = np.asarray(ta, dtype=float)
    rh = np.asarray(rh, dtype=float)
    ghi = np.nan_to_num(np.asarray(ghi, dtype=float), nan=0.0)
    dni = np.nan_to_num(np.asarray(dni, dtype=float), nan=0.0)
    dhi = np.nan_to_num(np.asarray(dhi, dtype=float), nan=0.0)
    solar_elevation = np.asarray(solar_elevation, dtype=float)
    cloud_fraction = np.nan_to_num(np.asarray(cloud_fraction, dtype=float), nan=0.0)

    # ------------------------------------------------------------------
    # Short-wave absorbed (direct + diffuse + ground-reflected)
    # ------------------------------------------------------------------
    daylight = solar_elevation > 0
    fp = _projected_area_factor(solar_elevation)
    s_dir = np.where(daylight, fp * dni * sun_exposure, 0.0)
    s_diff = 0.5 * dhi
    s_ref = 0.5 * ghi * albedo
    s_abs = ALPHA_SW * (s_dir + s_diff + s_ref)

    # ------------------------------------------------------------------
    # Long-wave absorbed (sky + ground)
    # ------------------------------------------------------------------
    epsilon_sky = _sky_emissivity(ta, rh, cloud_fraction)
    ta_k = ta + 273.15
    l_down = epsilon_sky * SIGMA * ta_k**4

    t_ground = ta + heating_k * ghi
    l_up = EPSILON_GROUND * SIGMA * (t_ground + 273.15) ** 4

    l_abs = EPSILON_BODY * (0.5 * l_down + 0.5 * l_up)

    # ------------------------------------------------------------------
    # Stefan-Boltzmann inversion
    # ------------------------------------------------------------------
    total_flux = s_abs + l_abs
    mrt_k = (total_flux / (EPSILON_BODY * SIGMA)) ** 0.25
    return mrt_k - 273.15
