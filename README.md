# Evinced Mobile Products Dashboard

Automated pipeline that pulls live scan data from Coralogix + Pendo, builds an interactive HTML dashboard, and renders a PDF — with a daily scheduled refresh.

## What it does

1. **Fetches scan data** from Coralogix (last 14 days) — tenants, users, scan counts, issues
2. **Fetches latest scan timestamps** per tenant from Coralogix
3. **Rebuilds the HTML dashboard** — filterable by product, SDK type, date range
4. **Renders a PDF** from the HTML using Playwright/Chromium
5. **Posts a Slack notification** to `#mobile_analytics` on completion

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/<your-username>/evinced-mobile-dashboard.git
cd evinced-mobile-dashboard
```

### 2. Configure secrets
```bash
cp .env.example .env
# Open .env and fill in CORALOGIX_API_KEY (and optionally SLACK_BOT_TOKEN)
```

### 3. Load environment variables
```bash
export $(grep -v '^#' .env | xargs)
```
Or on macOS/Linux, add those lines to your `~/.zshrc` or `~/.bashrc`.

### 4. Install Python dependencies
```bash
pip install playwright --break-system-packages
python3 -m playwright install chromium
```

## Running the dashboard

### Full refresh (all steps)
```bash
python3 refresh_all.py
```

### Individual steps
```bash
python3 fetch_with_sa.py            # Step 1 — Coralogix scan data
python3 fetch_latest_scan_dates.py  # Step 2 — latest scan timestamps
python3 rebuild_dashboard_v4.py     # Step 3 — build HTML
python3 render_pdf.py               # Step 4 — render PDF
```

### Serve the dashboard locally
```bash
python3 ../serve_dashboard.py
# Open: http://localhost:8080/mobile-products-dashboard.html
```

## Files

| File | Description |
|------|-------------|
| `fetch_with_sa.py` | Fetches 14-day scan data from Coralogix DataPrime |
| `fetch_latest_scan_dates.py` | Fetches per-tenant latest scan timestamp |
| `rebuild_dashboard_v4.py` | Generates the interactive HTML dashboard |
| `render_pdf.py` | Renders HTML → PDF using Playwright |
| `refresh_all.py` | Orchestrator: runs all steps + posts to Slack |
| `mfa_events.csv` | Pendo MFA feature activity data (update manually each month) |
| `.env.example` | Template for secrets — copy to `.env` |

## Data sources

- **Coralogix** — raw scan telemetry (MobileAnalysis events), TIER_ARCHIVE
- **Pendo** — MFA feature engagement (CSV export, updated manually)

## Notes

- Data JSON files (`rows_with_sa.json`, `latest_scan_dates.json`) are generated on each run and are excluded from git.
- The Pendo CSV (`mfa_events.csv`) is a manual export — update it when you have fresh Pendo data.
- `render_pdf.py` auto-installs Playwright/Chromium if they are not present.
