# 🌿 Breathe ESG — Enterprise Carbon Accounting Platform

### 🚀 **Live Demo:** [https://breatheesg1.netlify.app/](https://breatheesg1.netlify.app/)

*(Note: The backend is hosted on a free **Render** tier, which sleeps after 15 minutes of inactivity. Please allow 30-50 seconds for the initial data to load when first opening the link!)*

---

## ☁️ Deployment Architecture
This application is fully deployed and live on the internet using modern cloud infrastructure:
* **Frontend Hosting:** [Netlify](https://www.netlify.com/) (Continuous Deployment from GitHub)
* **Backend API Hosting:** [Render](https://render.com/) (Gunicorn WSGI Server)
* **Production Database:** PostgreSQL Managed Database on Render

## 📖 Overview
Breathe ESG is a full-stack web application designed to solve one of the most tedious challenges in carbon accounting: **data ingestion and normalisation**. 

Enterprise companies track their emissions (Scope 1, 2, and 3) across disparate systems like SAP (procurement), utility portals (electricity), and Navan/Concur (corporate travel). This application ingests these different raw formats (CSV, JSON), normalises them into a single unified schema, and surfaces a Review Dashboard where sustainability analysts can inspect, flag, and approve records before they are locked for audit.

## 🛠️ Tech Stack

This project was built using a modern, decoupled architecture:

* **Frontend:** React.js, Vite, Vanilla CSS (Custom Design System)
* **Backend:** Python, Django, Django REST Framework
* **Database:** PostgreSQL (Production) / SQLite (Local)
* **Infrastructure:** Gunicorn, WhiteNoise, dj-database-url

```text
┌─────────────────┐     ┌──────────────┐     ┌───────────────┐
│  React Frontend │────▶│  Django REST  │────▶│  PostgreSQL   │
│    (Netlify)    │◀────│   (Render)   │◀────│   (Render)    │
└─────────────────┘     └──────────────┘     └───────────────┘
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
              SAP Parser  Utility    Travel
              (CSV)       Parser     Parser
                          (CSV)      (JSON)
```

## ✨ Key Features & Technical Achievements

1. **Multi-Tenant Architecture:** The database is designed for SaaS scale. Every piece of data is linked to a `Tenant`, ensuring strict data isolation between different corporate clients.
2. **Robust File Parsing Engine:** 
   - Handles SAP flat-file CSV exports (supports both English and German headers, comma or semicolon delimiters).
   - Handles standard Utility Portal meter readings.
   - Parses complex Corporate Travel JSON responses from APIs like Navan/Concur.
3. **Automated Classification:** Automatically maps raw activities to specific Scopes (e.g., Electricity -> Scope 2, Flights -> Scope 3, Diesel -> Scope 1).
4. **Data Quality Flags:** The ingestion engine automatically flags anomalies (e.g., massive spikes in electricity usage, unknown units, missing dates) for human review.
5. **Data Provenance (Audit Trail):** To ensure auditability, the original verbatim raw payload of every row is stored permanently alongside the normalised data.
6. **Bulk Review Workflow:** A React dashboard built for analysts, allowing them to filter by source, scope, and status, and bulk-approve or reject records efficiently.

## 🧪 Testing the Live App

If you are viewing the live demo and want to test the data ingestion pipeline, you can use the sample files provided in this repository!

1. Download one of the sample files located in the [`backend/sample_data/`](https://github.com/shachiring/Breathe_ESG/tree/main/backend/sample_data) directory.
2. Go to the **Ingest Data** tab on the live website.
3. Upload the corresponding file.
4. Return to the **Review Dashboard** to see the data successfully parsed, classified, and awaiting your review.

## 💻 Local Development Setup

If you wish to run the project locally on your machine:

### Prerequisites
- Python 3.11+
- Node.js 18+

### Backend (Django)
```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
*API will run at `http://localhost:8000/api/`*

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```
*Dashboard will run at `http://localhost:5173/`*

---
*Developed as a technical showcase for enterprise software engineering and full-stack architecture.*
