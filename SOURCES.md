# Sources — Breathe ESG

For each of the three data sources: what real-world format we researched, what we learned, what our sample data looks like and why, and what would break in a real deployment.

---

## 1. SAP — Fuel & Procurement Data

### What we researched

SAP stores procurement data across several tables:
- **EKKO** (Purchase Order header) — vendor, company code, currency.
- **EKPO** (Purchase Order item) — material, quantity, unit, plant.
- **MSEG** (Material document segment) — goods movements, posting dates.

Data can be extracted via:
- **SE16 table export** — manual CSV/Excel download from the SAP GUI.
- **IDoc → middleware (PI/PO, CPI)** — automated EDI/flat-file generation.
- **OData / BAPI** — programmatic API access (S/4HANA).

We chose **flat-file CSV** because it's the most common format for enterprise clients who don't have middleware licenses or haven't migrated to S/4HANA.

### What we learned

- **German headers are real.** SAP installations in DACH regions use German field labels by default: `Menge` (quantity), `Buchungsdatum` (posting date), `Materialkurztext` (material description).
- **Semicolons, not commas.** European locale CSV exports use `;` as the field delimiter and `,` as the decimal separator.
- **Unit codes are SAP-internal.** `ST` = pieces (Stück), `L` = liters, `KG` = kilograms, `TO` = tonnes.  These don't match ISO standards.
- **Plant codes are opaque.** `1010`, `1020`, `1030` mean nothing without a lookup table (`T001W`).  We accept them as-is and store in `original_payload`.

### What our sample data looks like

```csv
Belegnummer;Werk;Materialkurztext;Menge;MEINS;Buchungsdatum;Warengruppe;Bewegungsart;CO2_Faktor
4500012301;1010;Diesel Kraftstoff;2500;L;15.01.2025;Diesel;101;2.68
```

- 15 rows covering diesel, petrol, natural gas, LPG, heating oil (fuels → Scope 1) and office supplies, IT hardware, cleaning supplies (procurement → Scope 3).
- One row with a missing emission factor to test flagging.
- All dates in `DD.MM.YYYY` format (German standard).
- Movement type `101` = goods receipt (the most common posting for procurement).

### What would break in a real deployment

- **Multi-level BOM explosions:** A single PO item might resolve to 50 sub-components with different emission factors.  We treat each row atomically.
- **Currency / price-based emissions:** Some Scope 3 methodologies use spend-based factors (kgCO2e per $).  We don't handle this.
- **Plant-to-location mapping:** Emission factors depend on where the fuel is combusted.  Without a plant → geography lookup, we can't apply regional factors.
- **SAP change logs:** If a PO is amended after initial posting, the export might contain both versions.  We'd need deduplication logic.

---

## 2. Utility — Electricity Data

### What we researched

Facilities teams get electricity data from:
- **Utility portal CSV exports** — PG&E, Duke Energy, National Grid, Enel all offer downloadable CSVs.
- **Green Button data** — a US DOE standard (XML/JSON) for customer energy data, available from ~50 US utilities.
- **PDF bills** — the most common format, but the hardest to parse (no standard layout).
- **Smart meter APIs** — some advanced metering infrastructure (AMI) offers real-time interval data.

We chose **portal CSV** because it's universally available and machine-readable.

### What we learned

- **Billing periods ≠ calendar months.** A bill might cover Jan 3 – Feb 2, and the next covers Feb 3 – Mar 4.  Pro-rating to calendar months requires allocation logic.
- **Multiple meters per account.** A single corporate account might have 20 meters across different buildings.  Each meter has its own readings.
- **Demand vs consumption.** Utilities bill on both consumption (kWh) and demand (kW peak).  For emissions, only consumption matters.
- **Tariff structures vary.** Time-of-use, tiered, flat-rate.  Irrelevant for emissions but useful for cost allocation.

### What our sample data looks like

```csv
Account Number,Meter ID,Service Address,Read Date Start,Read Date End,Usage (kWh),Demand (kW),Cost ($),Tariff,Notes
ACC-90210,MTR-001,"123 Industrial Blvd, Houston TX",2025-01-01,2025-01-31,42350,185,5482.50,Commercial-TOU,
```

- 12 rows across 2 accounts and 4 meters.
- Meter MTR-002 has a suspicious spike in March (55,200 kWh vs ~19,000 in previous months) — triggers our spike detection flag.
- Meter MTR-004 is a data center with consistently high baseline (~89,000 kWh/month).
- All units are kWh.

### What would break in a real deployment

- **Net metering / solar.** If the facility has on-site solar, the export might show negative values (energy exported to grid).  Our parser would flag these.
- **Estimated readings.** Utilities sometimes estimate readings between actual meter reads.  The CSV won't always tell you which are estimated.
- **Multiple fuel types.** Some facilities use natural gas for heating (separate utility, separate meter, Scope 1 not Scope 2).  Our parser assumes all utility data is electricity.
- **MWh vs kWh.** Large industrial meters report in MWh.  We handle this with a unit multiplier, but a column labelled "Usage" without a unit header would fail silently.

---

## 3. Corporate Travel — Navan / Concur

### What we researched

- **Navan (formerly TripActions):** Offers a REST API and admin console CSV/ZIP exports.  The sustainability report includes booking_id, traveler, category, CO2 emissions, calculation methodology (DEFRA/ICAO/TREMOD).
- **SAP Concur:** Provides travel data through the Concur Travel API and partners with Thrust Carbon for ISO 14083-assured emissions data.
- **Common data shape:** Both platforms provide booking-level detail: category (FLIGHT/HOTEL/GROUND/RAIL), distance, cabin class, cost.

We chose to simulate a **Navan API response** (JSON with a `bookings` array) because:
1. Navan's API shape is well-documented.
2. JSON is the natural format for API-driven ingestion.
3. The parser can trivially switch from file-read to HTTP GET when credentials are available.

### What we learned

- **Distance isn't always provided.** Some bookings only have airport codes (IATA 3-letter).  You need a distance lookup or geodesic calculation.
- **Cabin class matters.** Business/first-class flights have ~3× the emission factor of economy (more space per passenger = more fuel allocated).
- **Hotel emissions vary wildly.** A budget hotel in India ≈ 5 kgCO2e/night; a luxury hotel in New York ≈ 50 kgCO2e/night.  DEFRA provides an average (20.6 kgCO2e/night) which we use as a fallback.
- **Ground transport is noisy.** Rides may be taxis, Ubers, rental cars, or shuttles.  Each has a different factor, but the data often just says "GROUND".

### What our sample data looks like

```json
{
  "booking_id": "NVN-2025-00101",
  "traveler_name": "Priya Sharma",
  "category": "FLIGHT",
  "departure_code": "BOM",
  "arrival_code": "DEL",
  "distance_km": null,
  "cabin_class": "Economy",
  "co2_kg": null,
  "booking_date": "2025-01-15"
}
```

- 10 bookings: 4 flights, 3 hotel stays, 2 ground transport, 1 rail.
- Flight BOM→DEL has no distance — triggers our airport lookup table (1,148 km).
- Flight DEL→DXB has no distance and no lookup entry — flagged for review.
- International business-class flight LHR→JFK demonstrates the higher emission factor (0.74 vs 0.255 kg/km).
- Rail trip DEL→AGR uses a low factor (0.035 kg/km) showing rail's carbon advantage.

### What would break in a real deployment

- **Multi-leg flights.** BOM→DEL→LHR would appear as two segments, but the platform might report it as one booking.  Our parser treats each booking atomically.
- **Cancelled bookings.** The API response might include cancelled trips that shouldn't count toward emissions.  We'd need a `status` filter.
- **Currency conversion for cost.** Our sample uses INR, but a multinational might have bookings in 10+ currencies.  Irrelevant for emissions but matters for financial reconciliation.
- **Rate of API calls.** Navan's API has rate limits.  A production scheduler would need retry logic and incremental syncing (last-sync timestamp).
