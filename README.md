# Breathe ESG — Emissions Data Ingestion & Review Platform

A full-stack prototype (Django REST + React) that ingests emissions and activity data from three enterprise sources, normalises it into a unified schema, and surfaces a review dashboard where analysts can inspect, flag, approve, and reject records before they're locked for audit.

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- pip, npm

### Backend (Django)
```bash
cd backend
pip install django djangorestframework django-cors-headers
python manage.py migrate
python manage.py seed_demo      # Load sample data
python manage.py runserver
```
API is available at `http://localhost:8000/api/`

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```
Dashboard is available at `http://localhost:5173/`

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌───────────────┐
│  React Frontend │────▶│  Django REST  │────▶│   SQLite /    │
│   (Vite)        │◀────│  Framework   │◀────│  PostgreSQL   │
└─────────────────┘     └──────────────┘     └───────────────┘
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
              SAP Parser  Utility    Travel
              (CSV)       Parser     Parser
                          (CSV)      (JSON)
```

## Data Sources

| Source | Format | Scope | Ingestion |
|--------|--------|-------|-----------|
| SAP (Fuel & Procurement) | CSV flat file (semicolon/comma) | Scope 1 (fuels), Scope 3 (goods) | File upload |
| Utility (Electricity) | Portal CSV export | Scope 2 | File upload |
| Corporate Travel (Navan) | JSON (API response shape) | Scope 3 | File upload |

## Key Features

- **Multi-tenant data model** with tenant isolation
- **Automatic scope classification** (Scope 1/2/3) based on source and activity type
- **Smart data quality flags** — spike detection, missing values, unknown units
- **Original payload preservation** — every normalised row stores the raw source data for audit
- **Bulk approve/reject workflow** — analysts can review and action records en masse
- **Filter by source, scope, and status** — focused review of specific data slices

## Documentation

- [`MODEL.md`](MODEL.md) — Data model design and rationale
- [`DECISIONS.md`](DECISIONS.md) — Ambiguity resolution log
- [`TRADEOFFS.md`](TRADEOFFS.md) — What we deliberately didn't build
- [`SOURCES.md`](SOURCES.md) — Research on each data source

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats/` | Dashboard summary (counts, scope totals) |
| GET | `/api/records/` | List emission records (filterable) |
| POST | `/api/records/bulk_review/` | Bulk approve/reject |
| POST | `/api/ingest/?source_type=SAP&tenant_id=1` | Upload and ingest data |
| GET | `/api/tenants/` | List tenants |
| GET | `/api/imports/` | List import history |

## Sample Data

Located in `backend/sample_data/`:
- `sap_export.csv` — 15 rows of SAP procurement/fuel data with German headers
- `utility_export.csv` — 12 rows of electricity meter readings with a usage spike
- `travel_bookings.json` — 10 Navan-style travel bookings (flights, hotels, ground, rail)
