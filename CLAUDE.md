# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A flat set of Python 3 scripts that pull Mobile SDK/MFA telemetry from Coralogix (and optionally Zendesk), merge it with a Pendo CSV export and HubSpot account metadata, emit a single self-contained interactive HTML dashboard, render it to PDF via Playwright/Chromium, and post a Slack summary. No packaging, no dependencies beyond `playwright` and the stdlib.

## Commands

```bash
# Full pipeline (4 steps + Slack post)
python3 refresh_all.py

# Individual steps
python3 fetch_with_sa.py            # Coralogix 14-day scan rows → rows_with_sa.json
python3 fetch_latest_scan_dates.py  # per-tenant last-scan → latest_scan_dates.json
python3 rebuild_dashboard_v4.py     # build HTML (reads all JSON + mfa_events.csv)
python3 render_pdf.py               # HTML → PDF via Playwright Chromium

# Standalone — NOT in refresh_all.py
python3 fetch_zendesk.py            # ticket counts per tenant → zendesk_tickets.json

# Dependencies (first-time setup)
pip install playwright --break-system-packages
python3 -m playwright install chromium
```

`render_pdf.py` auto-installs Playwright/Chromium if missing, so it can run on a fresh host.

## Environment

Required in `.env` (see `.env.example`):
- `CORALOGIX_API_KEY` — used by both Coralogix fetch scripts. Scripts raise `EnvironmentError` at import if missing.
- `SLACK_BOT_TOKEN` — optional; `refresh_all.py` skips the Slack post if unset.

Not in `.env.example` but required for `fetch_zendesk.py`:
- `ZENDESK_SUBDOMAIN`, `ZENDESK_EMAIL`, `ZENDESK_API_TOKEN`

HubSpot is **not** fetched by any script in this repo — it is populated via an MCP connector in Cowork and left on disk as `hubspot_accounts.json`. `rebuild_dashboard_v4.py` reads it if present and falls back to a large hardcoded `_FALLBACK` dict otherwise.

## Architecture — things that are not obvious from file names

**Output location.** Every script uses `BASE = dirname(__file__)`. Fetch scripts write their JSON next to themselves (`BASE`); `rebuild_dashboard_v4.py` and `render_pdf.py` write `mobile-products-dashboard.{html,pdf}` into `BASE/output/` (auto-created). The `output/` directory is gitignored. In the deployed `mnt/outputs/dashboard-scripts/` layout, the original intent was the parent directory — if you re-deploy, update `OUTPUTS` in `rebuild_dashboard_v4.py`, `render_pdf.py`, and `refresh_all.py`.

**Data flow.**
```
Coralogix ──fetch_with_sa──▶ rows_with_sa.json ─┐
Coralogix ──fetch_latest──▶ latest_scan_dates.json ─┤
Pendo (manual CSV) ──▶ mfa_events.csv ───────────────┤
HubSpot (via MCP) ──▶ hubspot_accounts.json ─────────┼──▶ rebuild_dashboard_v4 ──▶ HTML ──▶ render_pdf ──▶ PDF
Zendesk (optional) ──▶ zendesk_tickets.json ─────────┘
                                                     │
timeseries_new.json (legacy, still required) ────────┘
```

`rebuild_dashboard_v4.py` also requires `timeseries_new.json` to be present — it is `json.load`ed unconditionally at the top. No script in the repo generates it; treat it as an input you must have on disk.

**`rebuild_dashboard_v4.py` is one giant f-string.** The file is ~1,170 lines and ends with `f.write(html)` — the HTML, CSS, and Chart.js/vanilla-JS payload are all built from a single Python f-string with JSON blobs spliced in. Two consequences when editing:
- Every literal `{` or `}` in the HTML/JS body must be doubled (`{{` / `}}`) or Python will try to interpret it as a format field.
- Data passed to JS goes through the `*_js = json.dumps(...)` variables near line 330; the template references them by name.

**SDK naming lives in one place.** `SDK_TYPE_NORM` and `SDK_VARIANT_NORM` dicts (around line 61–88 of `rebuild_dashboard_v4.py`) are the single source of truth for collapsing Coralogix raw values (e.g. `ESPRESSO_SDK`, `APPIUM_JAVA_SDK`) into display names (`Espresso`, `Appium`). Add new SDK variants there — filters, charts, and the `SDK_PRODUCT_TYPES` set all depend on the normalized forms.

**Internal tenants are filtered via `INTERNALS`.** Hardcoded set around line 106. Used for the "exclude internal" toggle; keep this in sync with tenant naming in Coralogix.

**Slack channel ID is hardcoded** in `refresh_all.py` (`SLACK_CHANNEL = "C0AT76PV6F6"` → `#mobile_analytics`).

## Generated vs. committed files

`.gitignore` excludes all pipeline outputs — `rows_with_sa.json`, `latest_scan_dates.json`, `timeseries_new.json`, `hubspot_accounts.json`, `zendesk_tickets.json`, and the HTML/PDF. The only data file committed to the repo is `mfa_events.csv`, which is a **manual** monthly Pendo export — the `pendo_date_range` string in `rebuild_dashboard_v4.py` (currently `"Apr 1 – Apr 16, 2026"`) must be updated by hand when the CSV is refreshed.
