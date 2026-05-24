# Decisions — Breathe ESG

Every ambiguity we encountered, what we chose, and what we'd ask the PM if we could.

---

## 1. SAP: Which export format?

**Ambiguity:** SAP data can come via IDoc, BAPI, OData, or flat-file exports.

**Decision:** We handle **flat-file CSV exports** (the output of an SE16 table dump or IDoc-to-CSV middleware pipeline).

**Why:**
- Flat files are the lowest common denominator — they work regardless of which SAP version the client runs (ECC, S/4HANA, BW).
- Many large enterprises still use file-based interfaces for cross-system data movement.
- IDoc processing requires SAP middleware (PI/PO or CPI), which is outside the scope of a 4-day prototype.

**What we'd ask the PM:**
- "Does this client have SAP CPI or PI/PO?  If yes, we could build an OData pull instead of file upload."
- "What tables are they exporting — EKPO only, or do they join MSEG for goods movements?"

---

## 2. SAP: Delimiter and encoding

**Ambiguity:** European SAP installations often use semicolons instead of commas and encode files in Latin-1.

**Decision:** We auto-detect the delimiter (using Python's `csv.Sniffer`) and try UTF-8 before falling back to Latin-1.

**Why:**
- Hardcoding comma-only would silently fail on German installations.
- Two encoding attempts cover >95% of real SAP exports.

---

## 3. SAP: Scope assignment for procurement

**Ambiguity:** SAP procurement data contains both fuel (Scope 1) and purchased goods (Scope 3).

**Decision:** We classify by material group (`Warengruppe`). Known fuel groups → Scope 1; everything else → Scope 3.

**Why:**
- Material group is always present in SAP exports and is the standard classification field.
- A production system would use a configurable mapping table, but the principle is sound.

**What we'd ask:**
- "Is there a client-specific material group hierarchy, or are we using SAP standard?"

---

## 4. Utility: Portal CSV vs PDF vs API

**Ambiguity:** Electricity data can come from PDF bills, portal CSVs, or Green Button APIs.

**Decision:** **Portal CSV export.**

**Why:**
- PDF parsing (OCR, regex extraction) is fragile, slow, and requires Tesseract/AWS Textract.  Not viable in 4 days.
- Green Button APIs (for US utilities) require OAuth credentials and utility-specific registration.
- Portal CSV is what facilities teams actually use day-to-day — they log in, download last month's data, and email it.

**What we'd ask:**
- "Does this client have a Green Button-compatible utility?  If yes, we could automate the pull."
- "How many meters/accounts are we dealing with?"

---

## 5. Utility: Emission factor

**Ambiguity:** Grid emission factors vary by region, time of day, and methodology (location-based vs market-based).

**Decision:** We use a single average factor (0.207 kgCO2e/kWh, UK DEFRA 2024 grid average) for the prototype.

**Why:**
- Location-based factors require a grid region lookup table (eGRID subregions for the US, AIB residual mix for EU).
- Market-based factors depend on RECs/PPAs the client has purchased.
- For a prototype, a single factor demonstrates the architecture without requiring a factor database.

**What we'd ask:**
- "Location-based or market-based reporting?"
- "Which country/region grids are relevant?"

---

## 6. Utility: Spike detection

**Ambiguity:** How do we define "suspicious" consumption?

**Decision:** A row is flagged if its usage is >2× the previous row's usage (sequential order within the same file).

**Why:**
- Simple, explainable heuristic that catches common anomalies (meter resets, estimated readings, seasonal spikes).
- A production system would use rolling averages, seasonal decomposition, or z-score analysis.

---

## 7. Travel: Navan API vs file upload

**Ambiguity:** Travel data can come from Navan API, Concur API, or file exports.

**Decision:** We accept **JSON file upload** in the shape of a Navan API response.

**Why:**
- We don't have Navan API credentials.
- By designing the parser to accept the exact shape of a Navan API response, switching to a live API pull is a one-line change (swap file-read for HTTP GET).
- The JSON structure was researched from Navan's documentation and sustainability export format.

**What we'd ask:**
- "Can we get Navan sandbox credentials, or should we pull from a staging webhook?"

---

## 8. Travel: Missing distances

**Ambiguity:** Navan sometimes provides only airport codes, not distances.

**Decision:** We maintain a small lookup table of great-circle distances for common routes (BOM-DEL, LHR-JFK, etc.).  If the route isn't in the table, the row is flagged.

**Why:**
- A production system would call a geodesic API (OpenFlights, AviationStack, or haversine formula on coordinates).
- The lookup table demonstrates the pattern without an external API dependency.

---

## 9. Multi-tenancy approach

**Ambiguity:** Row-level security vs schema-per-tenant vs application-level filtering.

**Decision:** Application-level filtering (every query includes `tenant_id`).

**Why:**
- Simplest to implement for a prototype.
- Schema-per-tenant requires dynamic routing and migration management (django-tenants).
- Row-level security in PostgreSQL is the right production answer, but SQLite doesn't support it.

---

## 10. Authentication

**Ambiguity:** The assignment says "share credentials to log in", implying some auth is expected.

**Decision:** We use Django's admin for superuser access.  The analyst dashboard is open for the prototype.

**Why:**
- Building a full auth flow (login page, session management, RBAC) would consume ~1 day and distract from the data model.
- The admin panel already provides a working auth layer for the evaluators.

**What we'd ask:**
- "Do analysts need individual accounts, or is a shared team login acceptable?"

---

## 11. Database

**Ambiguity:** SQLite vs PostgreSQL.

**Decision:** SQLite for local development, PostgreSQL for deployment.

**Why:**
- SQLite requires zero configuration and ships with Python.
- Django's ORM abstracts the difference — switching is a one-line settings change.
- PostgreSQL is required for production (JSONField indexing, concurrent writes, row-level security).
