# Tradeoffs — Breathe ESG

Three things we deliberately did not build, and why.

---

## 1. Emission Factor Management System

**What it would be:** A normalised database table (`EmissionFactor`) with columns for factor value, unit, source (DEFRA, EPA, GHG Protocol), vintage year, region, and methodology (location-based vs market-based).  A CRUD interface for admins to upload new factor tables annually.

**Why we didn't build it:**
- The current architecture hardcodes factors in each parser (e.g. `GRID_FACTOR = 0.207` in the utility parser, `0.255 kg/passenger-km` for flights).
- This is intentional for the prototype: it keeps the parsers self-contained and easy to read.
- In production, a `quantity × factor = emissions` pipeline would query this table at ingestion time, and factors would be versioned (the 2024 DEFRA table differs from 2023).

**The cost of not building it:**
- Updating a factor requires a code change and redeployment.
- We can't support regional variation (e.g. different grid intensity for Texas vs California).
- Factor auditing ("which factor vintage was used to compute this row's emissions?") isn't possible.

---

## 2. Real-Time Data Connectors (API Polling / Webhooks)

**What it would be:** A scheduler (Celery Beat or Django-Q) that polls the Navan API on a cron schedule (e.g. daily at midnight), automatically ingesting new bookings.  For utilities, a webhook endpoint that the utility portal could POST to when new readings are available.

**Why we didn't build it:**
- We don't have API credentials for any live system.
- A polling scheduler requires a task queue (Redis + Celery), which is significant infrastructure for a prototype.
- File upload covers the same functional need for the demo: an analyst uploads a CSV, the system normalises it.

**The cost of not building it:**
- Data ingestion is manual — someone has to download and upload files.
- There's no automated deduplication between API syncs (e.g. "this booking was already ingested yesterday").
- Latency: travel data won't appear until someone uploads it, which could be days after the trip.

---

## 3. Approval Workflow with Locking + Audit Log

**What it would be:** Once a record is approved, it becomes immutable — no edits, no re-review.  Every status change is recorded in an `AuditLog` table (who, when, old status, new status, notes).  Approved records are "locked for audit" and visible in a separate read-only view for external auditors.

**Why we didn't build it:**
- The current `APPROVED` status does mark a record as reviewed, and `reviewed_at` captures when.
- True immutability requires database-level controls (e.g. PostgreSQL triggers that prevent UPDATEs on approved rows) or a separate append-only audit table.
- An auditor-facing read-only view would be a separate React route with different permissions — effectively a second app.

**The cost of not building it:**
- An approved record can technically be un-approved or edited via the API (no lock enforcement).
- There's no diff history — if someone changes a record, we only know the current state, not what it was before.
- Auditors can't independently access the data without going through the analyst dashboard.

---

## Summary

| Feature | Effort (est.) | Why it matters | Why we skipped it |
|---------|---------------|---------------|-------------------|
| Emission factor table | ~1 day | Regional accuracy, factor versioning | Factors work inline for the demo |
| Real-time connectors | ~1.5 days | Automation, freshness | No credentials, needs Redis/Celery |
| Approval locking + audit log | ~1 day | Audit integrity | Status tracking covers the demo need |

All three are the natural next steps for a production deployment.
