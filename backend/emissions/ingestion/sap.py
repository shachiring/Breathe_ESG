"""
SAP Flat-File (CSV) Ingestion Parser
=====================================

Real-world context
------------------
SAP procurement / fuel data is typically extracted via:
  • SE16 table exports (e.g. EKPO, EKKO, MSEG)
  • IDoc → middleware → CSV pipeline
  • OData/BAPI dumps saved to flat files

The columns we handle here mirror a flattened EKPO + MSEG export:
  Belegnummer (Document Number), Werk (Plant), Materialkurztext (Material),
  Menge (Quantity), MEINS (Unit), Buchungsdatum (Posting Date), Warengruppe
  (Material Group), Bewegungsart (Movement Type), CO2_Faktor (Emission Factor).

Design decisions
----------------
- We accept *both* German and English header variants.
- Units are normalised to canonical forms (L → liters, KG → kg, etc.).
- Rows with missing quantity or unknown unit are flagged, not dropped.
- Scope assignment: fuels → Scope 1; purchased goods → Scope 3.
"""

import csv
import io
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

# Maps German SAP headers → internal canonical names
HEADER_MAP = {
    # German variants
    "belegnummer": "document_number",
    "werk": "plant_code",
    "materialkurztext": "material_description",
    "menge": "quantity",
    "meins": "unit",
    "buchungsdatum": "posting_date",
    "warengruppe": "material_group",
    "bewegungsart": "movement_type",
    "co2_faktor": "emission_factor",
    # English variants
    "document_number": "document_number",
    "doc_number": "document_number",
    "plant": "plant_code",
    "plant_code": "plant_code",
    "material": "material_description",
    "material_description": "material_description",
    "quantity": "quantity",
    "unit": "unit",
    "uom": "unit",
    "posting_date": "posting_date",
    "date": "posting_date",
    "material_group": "material_group",
    "movement_type": "movement_type",
    "emission_factor": "emission_factor",
}

# SAP unit codes → canonical units
UNIT_MAP = {
    "L": "liters",
    "LTR": "liters",
    "l": "liters",
    "KG": "kg",
    "kg": "kg",
    "ST": "pieces",
    "PC": "pieces",
    "M3": "m3",
    "GAL": "gallons",
    "TO": "tonnes",
    "T": "tonnes",
}

# Material groups that represent fuel (→ Scope 1)
FUEL_GROUPS = {"fuel", "diesel", "petrol", "gasoline", "natural_gas", "lng", "lpg", "heating_oil"}


def _normalise_headers(raw_headers):
    """Map raw CSV headers to canonical field names."""
    mapped = {}
    for h in raw_headers:
        key = h.strip().lower().replace(" ", "_").replace("-", "_")
        canonical = HEADER_MAP.get(key)
        if canonical:
            mapped[h] = canonical
        else:
            mapped[h] = key  # keep as-is for original_payload
    return mapped


def _parse_date(value):
    """Try multiple SAP date formats."""
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%Y%m%d", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def _parse_decimal(value):
    """Handle comma-as-decimal (German locale) and regular decimals."""
    if not value:
        return None
    try:
        cleaned = value.strip().replace(",", ".")
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def parse_sap_csv(file_content: bytes | str):
    """
    Parse an SAP flat-file CSV export.

    Returns a list of dicts, each containing:
      - normalised fields (quantity, unit, scope, activity_type, …)
      - original_payload (the raw row dict)
      - flag_reason (empty string if row is clean)
    """
    if isinstance(file_content, bytes):
        # Try UTF-8, fall back to latin-1 (common for SAP exports)
        try:
            text = file_content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = file_content.decode("latin-1")
    else:
        text = file_content

    # Auto-detect delimiter — SAP exports use semicolons in European locales
    first_line = text.split("\n", 1)[0]
    try:
        dialect = csv.Sniffer().sniff(first_line, delimiters=",;\t|")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ";" if first_line.count(";") > first_line.count(",") else ","

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

    header_map = _normalise_headers(reader.fieldnames or [])
    results = []

    for row_num, raw_row in enumerate(reader, start=2):
        original = dict(raw_row)
        mapped = {header_map.get(k, k): v.strip() if v else "" for k, v in raw_row.items()}

        flags = []

        # --- Quantity ---
        qty = _parse_decimal(mapped.get("quantity", ""))
        if qty is None:
            flags.append("Missing or unparseable quantity")

        # --- Unit ---
        raw_unit = mapped.get("unit", "").strip()
        unit = UNIT_MAP.get(raw_unit, raw_unit.lower() if raw_unit else "unknown")
        if unit == "unknown":
            flags.append(f"Unknown unit '{raw_unit}'")

        # --- Date ---
        date_val = _parse_date(mapped.get("posting_date", ""))
        if date_val is None:
            flags.append("Unparseable posting date")

        # --- Scope + Activity Type ---
        mat_group = mapped.get("material_group", "").lower().strip()
        if mat_group in FUEL_GROUPS:
            scope = "SCOPE_1"
            activity_type = f"Fuel — {mat_group.title()}"
        else:
            scope = "SCOPE_3"
            activity_type = f"Procurement — {mat_group.title() or 'General'}"

        # --- Emission factor ---
        factor = _parse_decimal(mapped.get("emission_factor", ""))
        emissions = None
        if qty is not None and factor is not None:
            emissions = qty * factor

        results.append({
            "quantity": qty or Decimal("0"),
            "unit": unit,
            "scope": scope,
            "activity_type": activity_type,
            "category": mat_group or "uncategorised",
            "period_start": date_val,
            "period_end": date_val,
            "emissions_kg_co2e": emissions,
            "original_payload": original,
            "flag_reason": "; ".join(flags),
        })

    return results
