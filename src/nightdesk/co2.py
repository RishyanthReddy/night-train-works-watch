"""Illustrative passenger transport scenarios based on German average factors."""

from math import isfinite
from types import MappingProxyType


SOURCE_URL = "https://www.umweltbundesamt.de/system/files/medien/366/bilder/dateien/vtv_2024_pv_tab_pdf.pdf"
REFERENCE_YEAR = 2024
RAIL_FACTOR = 26
ALTERNATIVES = MappingProxyType({"Car": 164, "Domestic air": 290, "Long-distance coach": 30})


def scenario_difference_kg(passengers: int, distance_km: float, share: float, alternative: str) -> float:
    """Return alternative minus rail in kg CO₂e for a hypothetical share between 0 and 1."""
    if type(passengers) is not int or passengers < 0:
        raise ValueError("Passenger count must be a non-negative whole number.")
    if not isfinite(distance_km) or distance_km < 0:
        raise ValueError("Distance must be finite and non-negative.")
    if not isfinite(share) or not 0 <= share <= 1:
        raise ValueError("Share must be between zero and one.")
    if alternative not in ALTERNATIVES:
        raise ValueError("Choose a listed transport mode.")
    difference = passengers * distance_km * share * (ALTERNATIVES[alternative] - RAIL_FACTOR) / 1000
    if not isfinite(difference):
        raise ValueError("The scenario exceeds the supported numeric range.")
    return difference
