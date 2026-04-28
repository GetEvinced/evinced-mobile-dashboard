# Evinced Mobile Products Dashboard

Automated pipeline that pulls live scan data from BigQuery + Zendesk, builds an interactive HTML dashboard, and renders a PDF — deployed on Google Cloud Run with a scheduled daily refresh.

## What it does

1. **Fetches scan data** from BigQuery (`production-267908`) — 14-day user-level rows + 90-day daily aggregates for charts
2. **Fetches latest scan timestamps** per tenant from BigQuery
3. **Fetches Zendesk tickets** — mobile/MFA tickets with severity, type, and monthly trend breakdowns
4. **Rebuilds the HTML dashboard** — filterable by product, SDK type, date range, tenant, SE owner, and weekends
5. **Renders a PDF** from the HTML using Playwright/Chromium
6. **Posts a Slack notification** to `#mobile_analytics` on completion

## Architecture

The dashboard runs as a **Google Cloud Run** service (`mobile-dashboard`) in project `ev-product-analytics`, region `us-central1`. It is deployed automatically via GitHub Actions on every push to `main`.

The `/refresh` endpoint runs all pipeline steps and writes the output HTML + PDF to `/tmp/dashboard-output/`. The `/mobile/` route serves the latest generated file.

## Setup (local development)

### 1. Clone the repo

```bash
git clone https://github.com/evinced/<repo>.git
cd <repo>
```

### 2. Authenticate with GCP

```bash
gcloud auth application-default login
```

The pipeline uses Application Default Credentials to query BigQuery in `production-267908`. No service account key file is needed locally.

### 3. Configure Zendesk credentials

Set these environment variables (or edit the defaults at the top of `fetch_zendesk.py`):

```bash
export ZENDESK_DOMAIN=https://evinced.zendesk.com
export ZENDESK_EMAIL=your@evinced.com
export ZENDESK_API_TOKEN=<your-token>
```

### 4. Install Python dependencies

```bash
pip install -r requirements.txt --break-system-packages
python3 -m playwright install chromium
```

## Running the dashboard

### Full refresh (all steps)

```bash
python3 refresh_all.py
```

### Individual steps

```bash
python3 fetch_with_sa.py              # Step 1 — BigQuery scan data (14d detail + 90d daily)
python3 fetch_latest_scan_dates.py    # Step 2 — latest scan timestamps per tenant
python3 fetch_zendesk.py              # Step 3 — Zendesk mobile/MFA tickets
python3 rebuild_dashboard_v4.py       # Step 4 — build interactive HTML
python3 render_pdf.py                 # Step 5 — render PDF
```

### Test the live server locally (via proxy)

```bash
# Terminal 1 — open authenticated proxy
gcloud run services proxy mobile-dashboard \
  --project=ev-product-analytics \
  --region=us-central1

# Terminal 2 — trigger a refresh
curl -X POST http://localhost:8080/refresh

# Then open http://localhost:8080/mobile/ in your browser
```

## Files

| File | Description |
|------|-------------|
| `fetch_with_sa.py` | Fetches 14-day user-level rows + 90-day daily aggregates from BigQuery |
| `fetch_latest_scan_dates.py` | Fetches per-tenant latest scan timestamp from BigQuery |
| `fetch_zendesk.py` | Fetches mobile/MFA Zendesk tickets — severity, type, monthly trend, raw list |
| `rebuild_dashboard_v4.py` | Generates the interactive HTML dashboard |
| `render_pdf.py` | Renders HTML → PDF using Playwright/Chromium |
| `refresh_all.py` | Orchestrator: runs all steps in order + posts to Slack |
| `requirements.txt` | Python dependencies |

## Data sources

- **BigQuery** (`production-267908.analytics`) — raw scan telemetry from `scan_success`, joined with tenant, user, SDK type, and product dimension tables
- **Zendesk** (`evinced.zendesk.com`) — mobile/MFA support tickets, filtered by keyword search
- **HubSpot** — owner, SE, TAM, renewal dates, new-tenant flags (hardcoded in `rebuild_dashboard_v4.py`; update manually)

## Dashboard features

- **Highlights panel** — biggest scan drop vs. prior period (red), new tenants (green), upcoming renewals (amber)
- **KPI cards** — active tenants, active users, total scans, new tenants, upcoming renewals, support tickets — all filter-aware
- **Charts** — Active Tenants Over Time, Total Scans Over Time, SDK Type Distribution, Zendesk by Severity, Zendesk by Product Area, SDK Type + Platform
- **Filters** — product (MFA / SDK), tenant, SDK type, date range (7 / 30 / 60 days / all / custom), show internals, SE owner, weekends toggle
- **Accounts table** — tenant-level summary with scan delta vs. prior period, row highlights for new/renewal/drop tenants
- **User detail table** — per-user scan breakdown, fully date-filtered

## Notes

- Generated JSON files (`rows_with_sa.json`, `daily_rows_90d.json`, `latest_scan_dates.json`, `zendesk_*.json`) are produced on each run and excluded from git.
- `render_pdf.py` auto-installs Playwright/Chromium on first run if not present.
- The Cloud Run service account (`mobile-dashboard-run@ev-product-analytics.iam.gserviceaccount.com`) requires `roles/bigquery.jobUser` and `roles/bigquery.dataViewer` on `production-267908`.
