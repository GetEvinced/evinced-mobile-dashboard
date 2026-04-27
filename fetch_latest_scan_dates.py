#!/usr/bin/env python3
"""
Fetch latest scan dates per tenant from BigQuery → latest_scan_dates.json

Uses the analytics.scan_success table, filtered to mobile products,
looking back 14 days to find the most recent scan per tenant.

Authentication: uses Application Default Credentials.
Run once: gcloud auth application-default login
Or set: GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
"""
import json, os
from datetime import datetime
from google.cloud import bigquery

BASE    = os.path.dirname(os.path.abspath(__file__))
PROJECT = "production-267908"

client = bigquery.Client(project=PROJECT)

QUERY = """
SELECT
  t.name AS tenantName,
  MAX(s.event_timestamp) AS latest_scan
FROM `production-267908.analytics.scan_success` s
LEFT JOIN `production-267908.analytics.tenants`    t ON s.tenant_id    = t.id
LEFT JOIN `production-267908.analytics.d_products` p ON p.id           = s.product_name
WHERE DATE(s._PARTITIONTIME) >= DATE_SUB(CURRENT_DATE(), INTERVAL 14 DAY)
  AND p.name IN ('MOBILE_SDK', 'MOBILE_FLOW_ANALYZER')
  AND t.name IS NOT NULL AND t.name != ''
GROUP BY 1
ORDER BY 1
"""

print("Querying BigQuery for latest scan dates…")
rows = list(client.query(QUERY).result())
print(f"Got {len(rows)} tenants")

out = {}
for r in rows:
    ts = r["latest_scan"]
    if ts:
        # ts is a datetime object from BigQuery
        if hasattr(ts, 'strftime'):
            formatted = ts.strftime('%b %-d, %Y')
        else:
            dt = datetime.fromisoformat(str(ts))
            formatted = dt.strftime('%b %-d, %Y')
        out[r["tenantName"]] = formatted

path = os.path.join(BASE, "latest_scan_dates.json")
with open(path, "w") as f:
    json.dump(out, f, indent=2)
print(f"Saved {len(out)} tenants to {path}")
