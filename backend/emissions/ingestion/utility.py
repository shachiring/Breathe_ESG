"""
Utility Portal CSV Ingestion Parser
====================================

Real-world context
------------------
Facilities teams typically download CSVs from utility portals
(e.g. PG&E Green Button, Duke Energy, Enel, National Grid).

A realistic portal CSV contains:
  Account Number, Meter ID, Service Address, Read Date Start,
  Read Date End, Usage (kWh), Demand (kW), Cost ($), Tariff, Notes.

Design decisions
----------------
- Billing periods may not align with calendar months — we store both
  start and end dates and let the analyst decide how to allocate.
- We normalise to kWh.  If MWh rows appear, we multiply by 1000.
- A spike threshold (>2× previous month) auto-flags a row for review.
- All electricity usage maps to Scope 2.
"""

import csv
import io
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

UNIT_NORMALISE = {
    "kwh": ("kWh", Decimal("1")),
    "kw h": ("kWh", Decimal("1")),
    "mwh": ("kWh", Decimal("1000")),
    "gwh": ("kWh", Decimal("1000000")),
    "wh": ("kWh", Decimal("0.001")),
}

HEADER_MAP = {
    "account_number": "account_number",
    "account": "account_number",
    "account_no": "account_number",
    "meter_id": "meter_id",
    "meter": "meter_id",
    "meter_number": "meter_id",
    "service_address": "service_address",
    "address": "service_address",
    "read_date_start": "period_start",
    "billing_start": "period_start",
    "start_date": "period_start",
    "period_start": "period_start",
    "read_date_end": "period_end",
    "billing_end": "period_end",
    "end_date": "period_end",
    "period_end": "period_end",
    "usage_kwh": "usage",
    "usage": "usage",
    "consumption": "usage",
    "consumption_kwh": "usage",
    "kwh": "usage",
    "demand_kw": "demand",
    "demand": "demand",
    "cost": "cost",
    "amount": "cost",
    "tariff": "tariff",
    "rate": "tariff",
    "unit": "unit",
    "uom": "unit",
    "notes": "notes",
}


def _normalise_headers(raw):
    mapped = {}
    for h in raw:
        key = h.strip().lower().replace(" ", "_").replace("-", "_").replace("(", "").replace(")", "")
        mapped[h] = HEADER_MAP.get(key, key)
    return mapped


def _parse_date(val):
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%d.%m.%Y", "%Y%m%d"):
        try:
            return datetime.strptime(val.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def _parse_decimal(val):
    if not val:
        return None
    try:
        cleaned = val.strip().replace(",", "").replace("$", "").replace("€", "")
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


# Emission factor for grid electricity (UK DEFRA 2024 average: ~0.207 kgCO2e/kWh)
GRID_FACTOR = Decimal("0.207")

# Spike detection: flag if usage > SPIKE_MULTIPLIER × previous row
SPIKE_MULTIPLIER = Decimal("2.0")


def parse_utility_csv(file_content: bytes | str):
    """
    Parse a utility portal CSV export for electricity data.

    Returns a list of normalised row dicts (same schema as sap.parse_sap_csv).
    """
    if isinstance(file_content, bytes):
        try:
            text = file_content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = file_content.decode("latin-1")
    else:
        text = file_content

    reader = csv.DictReader(io.StringIO(text))
    header_map = _normalise_headers(reader.fieldnames or [])
    results = []
    prev_usage = None

    for raw_row in reader:
        original = dict(raw_row)
        mapped = {header_map.get(k, k): (v.strip() if v else "") for k, v in raw_row.items()}

        flags = []

        # --- Usage ---
        usage_raw = _parse_decimal(mapped.get("usage", ""))
        raw_unit = mapped.get("unit", "kwh").strip().lower()
        unit_info = UNIT_NORMALISE.get(raw_unit, ("kWh", Decimal("1")))
        canonical_unit = unit_info[0]
        multiplier = unit_info[1]

        if usage_raw is not None:
            usage = usage_raw * multiplier
        else:
            usage = None
            flags.append("Missing or unparseable usage value")

        # --- Spike detection ---
        if usage is not None and prev_usage is not None and prev_usage > 0:
            if usage > prev_usage * SPIKE_MULTIPLIER:
                flags.append(f"Usage spike: {usage} vs previous {prev_usage}")
        prev_usage = usage

        # --- Dates ---
        period_start = _parse_date(mapped.get("period_start", ""))
        period_end = _parse_date(mapped.get("period_end", ""))
        if period_start is None:
            flags.append("Unparseable start date")

        # --- Emissions ---
        emissions = None
        if usage is not None:
            emissions = usage * GRID_FACTOR

        results.append({
            "quantity": usage or Decimal("0"),
            "unit": canonical_unit,
            "scope": "SCOPE_2",
            "activity_type": "Electricity",
            "category": "grid_electricity",
            "period_start": period_start,
            "period_end": period_end,
            "emissions_kg_co2e": emissions,
            "original_payload": original,
            "flag_reason": "; ".join(flags),
        })

    return results
