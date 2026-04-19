#!/usr/bin/env python3
"""Fetch real latest-scan timestamp per tenant from Coralogix → latest_scan_dates.json"""
import json, urllib.request, os
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))

API_KEY  = os.environ.get("CORALOGIX_API_KEY", "")
if not API_KEY:
    raise EnvironmentError("CORALOGIX_API_KEY environment variable is not set. "
                           "Copy .env.example to .env and fill in your key.")
ENDPOINT = "https://ng-api-http.cx498.coralogix.com/api/v1/dataprime/query"

now        = datetime.now(timezone.utc)
end_time   = now.strftime("%Y-%m-%dT%H:%M:%SZ")
start_time = (now - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ")

QUERY = """source logs
| filter $d.eventType == 'MobileAnalysis'
| groupby $d.tenantName agg max($m.timestamp) as latest_scan
| limit 500"""

payload = json.dumps({
    "query": QUERY,
    "metadata": {"startDate": start_time, "endDate": end_time,
                 "defaultSource": "logs", "tier": "TIER_ARCHIVE"}
}).encode("utf-8")

req = urllib.request.Request(ENDPOINT, data=payload,
    headers={"Authorization": f"Bearer {API_KEY}",
             "Content-Type": "application/json",
             "Accept": "application/json",
             "User-Agent": "Mozilla/5.0 (compatible; CoralogixClient/1.0)"},
    method="POST")

rows = []
with urllib.request.urlopen(req, timeout=120) as resp:
    for line in resp:
        line = line.decode("utf-8").strip()
        if not line: continue
        try:
            obj = json.loads(line)
            if "result" in obj:
                for item in obj["result"].get("results", []):
                    try: rows.append(json.loads(item.get("userData", "{}")))
                    except: pass
        except: pass

print(f"Got {len(rows)} tenant rows")

# Convert nanosecond timestamp → "Mon DD, YYYY"
dates = {}
for r in rows:
    tenant = r.get("tenantName")
    ts     = r.get("latest_scan")
    if not tenant or not ts:
        continue
    try:
        dt = datetime.utcfromtimestamp(int(ts) / 1_000_000_000)
        dates[tenant] = dt.strftime("%b %d, %Y")
    except Exception as e:
        print(f"  skip {tenant}: {e}")

print(f"Parsed {len(dates)} dates")
out = os.path.join(BASE, "latest_scan_dates.json")
with open(out, "w") as f:
    json.dump(dates, f, indent=2)
print(f"Saved → {out}")
