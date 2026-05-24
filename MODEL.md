# Data Model — Breathe ESG

## Overview

The data model is designed around three core principles:

1. **Multi-tenancy** — every row belongs to a `Tenant`, ensuring data isolation between client organisations.
2. **Auditability** — every ingested row stores its `original_payload` (the verbatim source data) alongside normalised fields, enabling full provenance tracking.
3. **Review workflow** — records pass through a status lifecycle (`PENDING → APPROVED / REJECTED`, or `FLAGGED → APPROVED / REJECTED`) before they're locked for audit.

---

## Entity-Relationship Diagram

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────────────┐
│   Tenant     │──1:N──│   DataImport     │──1:N──│   EmissionRecord     │
├──────────────┤       ├──────────────────┤       ├──────────────────────┤
│ id (PK)      │       │ id (PK)          │       │ id (PK)              │
│ name         │       │ tenant_id (FK)   │       │ tenant_id (FK)       │
│ industry     │       │ source_type      │       │ data_import_id (FK)  │
│ created_at   │       │ file_name        │       │ source_type          │
└──────────────┘       │ status           │       │ scope                │
                       │ total_rows       │       │ activity_type        │
                       │ failed_rows      │       │ category             │
                       │ error_summary    │       │ quantity             │
                       │ created_at       │       │ unit                 │
                       │ completed_at     │       │ emissions_kg_co2e    │
                       └──────────────────┘       │ period_start         │
                                                  │ period_end           │
                                                  │ original_payload     │
                                                  │ status               │
                                                  │ reviewer_notes       │
                                                  │ flag_reason          │
                                                  │ created_at           │
                                                  │ updated_at           │
                                                  │ reviewed_at          │
                                                  └──────────────────────┘
```

---

## Design Rationale

### Tenant

| Field     | Why |
|-----------|-----|
| `name`    | Human-readable client name for the dashboard. |
| `industry`| Emission factors and reporting requirements vary by sector. Stored here for future customisation. |

Multi-tenancy is enforced at the application level (every query filters by `tenant_id`).  In production, we'd add row-level security in PostgreSQL or use Django middleware to inject the tenant filter automatically.

### DataImport

Each ingestion event — whether a file upload or an API sync — gets its own `DataImport` row.  This serves as the **batch envelope**:

| Field          | Why |
|----------------|-----|
| `source_type`  | `SAP`, `UTILITY`, or `TRAVEL`.  Used to route to the correct parser. |
| `file_name`    | The original file name or API endpoint.  Critical for audit trail ("which export produced these numbers?"). |
| `status`       | `PROCESSING → COMPLETED / FAILED`.  Allows the UI to show import progress and surface errors. |
| `total_rows`   | How many rows the parser extracted from the file. |
| `failed_rows`  | How many rows could not be normalised.  A non-zero value here is a signal to the analyst. |
| `error_summary`| If the entire import fails (e.g. unparseable file), the stack trace or error message goes here. |

### EmissionRecord

This is the **single source of truth** — every row from every source is mapped into this schema.

#### Scope Classification

| Scope   | What maps here |
|---------|---------------|
| Scope 1 | SAP fuel purchases (diesel, petrol, LNG, LPG, heating oil) — direct combustion. |
| Scope 2 | Utility electricity consumption — indirect energy emissions. |
| Scope 3 | SAP procurement (non-fuel goods), all corporate travel. |

#### Key Design Choices

- **`original_payload` (JSONField):**  Stores the exact row from the CSV/JSON before any transformation.  If an analyst suspects a normalisation error, they can click "View" in the dashboard and compare the raw data side-by-side.

- **`quantity` + `unit`:**  Normalised to a canonical unit per activity type (liters for fuel, kWh for electricity, km for flights).  The unit is stored explicitly (not inferred) so the system never silently misinterprets the data.

- **`emissions_kg_co2e`:**  Computed during ingestion using published emission factors (DEFRA 2024).  Nullable — if we can't compute (e.g. missing emission factor in SAP), the field is null and the row is flagged.

- **`status` workflow:**  `PENDING` → analyst reviews → `APPROVED` or `REJECTED`.  Rows with data quality issues are automatically set to `FLAGGED` during ingestion.  `reviewed_at` timestamp creates an immutable audit record of when the decision was made.

- **`flag_reason`:**  Free-text field populated by the parser.  Examples: "Usage spike: 55200 vs previous 19100", "Distance estimated from BOM-DEL lookup", "Unknown unit 'GAL'".  This tells the analyst *why* the system thinks something is suspicious.

#### Indexes

```python
indexes = [
    models.Index(fields=["tenant", "status"]),   # Dashboard filters
    models.Index(fields=["source_type"]),          # Source filter
    models.Index(fields=["scope"]),                # Scope filter
]
```

These cover the three most common dashboard queries.  In production, we'd add a composite index on `(tenant, source_type, status)` for the main table view.

---

## What's Missing (Deliberately)

| Feature | Why it's out of scope |
|---------|----------------------|
| User/Role model | A 4-day prototype doesn't need RBAC.  In production, we'd use Django's auth + django-guardian for object-level permissions. |
| Emission factor table | Factors are currently hardcoded in the parsers.  A production system would have a normalised `EmissionFactor` table with vintage/region/methodology dimensions. |
| Edit history | `updated_at` tracks the last change, but we don't store a full diff log.  Django-reversion would solve this. |
| Allocation/apportionment | Billing periods that span months need pro-rating.  We store raw periods and leave allocation to a reporting layer. |
