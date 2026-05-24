"""
Corporate Travel (Navan / Concur) JSON Ingestion Parser
========================================================

Real-world context
------------------
Platforms like Navan expose a REST API returning JSON with booking-level
detail.  A typical response object contains:

  booking_id, traveler_name, category (FLIGHT / HOTEL / GROUND),
  departure_code, arrival_code, distance_km (may be null),
  cabin_class, hotel_nights, cost, currency, co2_kg (may be null),
  booking_date.

Design decisions
----------------
- If distance_km is null but we have airport codes, we use a lookup
  table of great-circle distances for major routes.  A production system
  would call a geodesic API (e.g. OpenFlights / IATA).
- If co2_kg is provided by the source we store it; otherwise we apply
  DEFRA-style factors per category.
- All travel is Scope 3 (Category 6: Business Travel).
"""

import json
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

# Approximate emission factors (kg CO2e per unit)
EMISSION_FACTORS = {
    "FLIGHT": Decimal("0.255"),        # per passenger-km, economy average
    "FLIGHT_BUSINESS": Decimal("0.740"),  # per passenger-km, business class
    "HOTEL": Decimal("20.6"),          # per room-night (DEFRA 2024 average)
    "GROUND": Decimal("0.171"),        # per vehicle-km, average car
    "RAIL": Decimal("0.035"),          # per passenger-km
}

# Simplified great-circle distances (km) for common routes when API doesn't provide distance
AIRPORT_DISTANCES = {
    ("BOM", "DEL"): 1148,
    ("DEL", "BOM"): 1148,
    ("BOM", "BLR"): 842,
    ("BLR", "BOM"): 842,
    ("DEL", "BLR"): 1740,
    ("BLR", "DEL"): 1740,
    ("JFK", "LAX"): 3983,
    ("LAX", "JFK"): 3983,
    ("LHR", "JFK"): 5555,
    ("JFK", "LHR"): 5555,
    ("SFO", "ORD"): 2966,
    ("ORD", "SFO"): 2966,
    ("SIN", "HKG"): 2581,
    ("HKG", "SIN"): 2581,
    ("DXB", "LHR"): 5471,
    ("LHR", "DXB"): 5471,
    ("FRA", "JFK"): 6198,
    ("JFK", "FRA"): 6198,
    ("BOM", "LHR"): 7189,
    ("LHR", "BOM"): 7189,
    ("DEL", "LHR"): 6713,
    ("LHR", "DEL"): 6713,
}


def _parse_decimal(val):
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError):
        return None


def _parse_date(val):
    if not val:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(val).strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def _estimate_flight_distance(dep, arr):
    """Look up approximate distance.  Returns km or None."""
    key = (dep.upper().strip(), arr.upper().strip())
    return AIRPORT_DISTANCES.get(key)


def parse_travel_json(file_content: bytes | str):
    """
    Parse a Navan-style JSON export.

    Accepts either a JSON array of bookings, or an object with a
    `bookings` key (mimicking a paginated API response).
    """
    if isinstance(file_content, bytes):
        text = file_content.decode("utf-8-sig")
    else:
        text = file_content

    data = json.loads(text)

    if isinstance(data, dict):
        bookings = data.get("bookings", data.get("data", data.get("results", [])))
    elif isinstance(data, list):
        bookings = data
    else:
        raise ValueError("Unexpected JSON structure — expected list or object with 'bookings' key.")

    results = []

    for booking in bookings:
        flags = []
        category = (booking.get("category") or booking.get("type") or "UNKNOWN").upper().strip()

        # --- Distance / quantity ---
        distance = _parse_decimal(booking.get("distance_km"))
        nights = _parse_decimal(booking.get("hotel_nights"))

        if category == "FLIGHT":
            if distance is None:
                dep = booking.get("departure_code", "")
                arr = booking.get("arrival_code", "")
                est = _estimate_flight_distance(dep, arr)
                if est:
                    distance = Decimal(str(est))
                    flags.append(f"Distance estimated from {dep}-{arr} lookup ({est} km)")
                else:
                    flags.append(f"No distance data; unknown route {dep}-{arr}")
                    distance = Decimal("0")

            cabin = (booking.get("cabin_class") or "economy").lower()
            factor_key = "FLIGHT_BUSINESS" if cabin in ("business", "first") else "FLIGHT"
            quantity = distance
            unit = "km"
            activity_type = f"Flight ({cabin.title()})"

        elif category == "HOTEL":
            quantity = nights or Decimal("1")
            unit = "room-nights"
            factor_key = "HOTEL"
            activity_type = "Hotel Stay"
            if nights is None:
                flags.append("Hotel nights not specified — defaulting to 1")

        elif category in ("GROUND", "CAR", "TAXI", "RIDE"):
            quantity = distance or Decimal("0")
            unit = "km"
            factor_key = "GROUND"
            activity_type = "Ground Transport"
            if distance is None:
                flags.append("No distance for ground transport")

        elif category == "RAIL":
            quantity = distance or Decimal("0")
            unit = "km"
            factor_key = "RAIL"
            activity_type = "Rail Travel"
            if distance is None:
                flags.append("No distance for rail trip")

        else:
            quantity = Decimal("0")
            unit = "unknown"
            factor_key = "GROUND"
            activity_type = f"Travel — {category.title()}"
            flags.append(f"Unrecognised travel category: {category}")

        # --- Emissions ---
        provided_co2 = _parse_decimal(booking.get("co2_kg"))
        if provided_co2 is not None:
            emissions = provided_co2
        else:
            factor = EMISSION_FACTORS.get(factor_key, Decimal("0"))
            emissions = quantity * factor

        # --- Date ---
        booking_date = _parse_date(
            booking.get("booking_date") or booking.get("travel_date") or booking.get("date")
        )

        results.append({
            "quantity": quantity,
            "unit": unit,
            "scope": "SCOPE_3",
            "activity_type": activity_type,
            "category": category.lower(),
            "period_start": booking_date,
            "period_end": booking_date,
            "emissions_kg_co2e": emissions,
            "original_payload": booking,
            "flag_reason": "; ".join(flags),
        })

    return results
