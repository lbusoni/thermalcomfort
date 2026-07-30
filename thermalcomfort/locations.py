"""Shared known locations registry.

This module centralizes the predefined locations originally used in the
interactive notebook, so they can be reused by CLI and Python API users.
"""

from __future__ import annotations

from .providers.base import LocationInfo

LOCATIONS: dict[str, LocationInfo] = {
    "Firenze": LocationInfo(43.7696, 11.2558, "Firenze"),
    "Livorno": LocationInfo(43.5485, 10.3106, "Livorno"),
    "Borgo San Lorenzo": LocationInfo(43.9543, 11.3882, "Borgo San Lorenzo"),
    "Maresca": LocationInfo(44.0533, 10.8488, "Maresca"),
    "Vada": LocationInfo(43.3516, 10.4555, "Vada"),
    "San Cassiano": LocationInfo(46.5792, 11.9246, "San Cassiano"),
    "Alghero": LocationInfo(40.5788, 8.3117, "Alghero"),
    "Chia": LocationInfo(38.8948, 8.8786, "Chia"),
    "Arbatax": LocationInfo(39.9766, 9.6874, "Arbatax"),
    "Roma": LocationInfo(41.9028, 12.4964, "Roma"),
    "Milano": LocationInfo(45.4642, 9.1900, "Milano"),
    "Venezia": LocationInfo(45.4408, 12.3155, "Venezia"),
    "Napoli": LocationInfo(40.8518, 14.2681, "Napoli"),
    "Palermo": LocationInfo(38.1157, 13.3615, "Palermo"),
    "Parigi": LocationInfo(48.8566, 2.3522, "Parigi"),
    "Londra": LocationInfo(51.5074, -0.1278, "Londra"),
    "Berlino": LocationInfo(52.5200, 13.4050, "Berlino"),
    "Barcellona": LocationInfo(41.3851, 2.1734, "Barcellona"),
    "Minorca": LocationInfo(39.9380, 3.9602, "Minorca"),
    "Atene": LocationInfo(37.9838, 23.7275, "Atene"),
    "Creta": LocationInfo(35.5172, 24.0172, "Creta"),
    "Stoccolma": LocationInfo(59.3293, 18.0686, "Stoccolma"),
    "Oslo": LocationInfo(59.9139, 10.7522, "Oslo"),
    "Reykjavik": LocationInfo(64.1265, -21.8174, "Reykjavik"),
    "New York": LocationInfo(40.7128, -74.0060, "New York"),
    "Los Angeles": LocationInfo(34.0522, -118.2437, "Los Angeles"),
    "Città del Messico": LocationInfo(19.4326, -99.1332, "Città del Messico"),
    "Buenos Aires": LocationInfo(-34.6037, -58.3816, "Buenos Aires"),
    "Città del Capo": LocationInfo(-33.9249, 18.4241, "Città del Capo"),
    "Dubai": LocationInfo(25.2048, 55.2708, "Dubai"),
    "Tokyo": LocationInfo(35.6762, 139.6503, "Tokyo"),
    "Singapore": LocationInfo(1.3521, 103.8198, "Singapore"),
    "Sydney": LocationInfo(-33.8688, 151.2093, "Sydney"),
}

_LOCATIONS_CASEFOLD_INDEX = {name.casefold(): name for name in LOCATIONS}


def get_known_location(name: str) -> LocationInfo:
    """Return a known location by name (case-insensitive)."""
    direct = LOCATIONS.get(name)
    if direct is not None:
        return direct

    canonical_name = _LOCATIONS_CASEFOLD_INDEX.get(name.casefold())
    if canonical_name is None:
        raise KeyError(name)
    return LOCATIONS[canonical_name]


def known_location_names() -> list[str]:
    """Return known location names sorted alphabetically."""
    return sorted(LOCATIONS)
