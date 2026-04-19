#!/usr/bin/env python3
"""Fetch rows grouped by all fields including both email AND serviceAccountId."""
import json, urllib.request, urllib.error, os
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))

API_KEY  = os.environ.get("CORALOGIX_API_KEY", "")
if not API_KEY:
    raise EnvironmentError("CORALOGIX_API_KEY environment variable is not set. "
                           "Copy .env.example to .env and fill in your key.")
ENDPOINT = "https://ng-api-http.cx498.coralogix.com/api/v1/dataprime/query"

now = datetime.now(timezone.utc)
end_time   = now.strftime("%Y-%m-%dT%H:%M:%SZ")
start_time = (now - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ")

QUERY = """source logs
| filter $d.eventType == 'MobileAnalysis'
| groupby $d.tenantName, $d.email, $d.serviceAccountId, $d.sdkType, $d.sdkVariant, $d.sdkVersion, $d.platformName,
formatTimestamp($m.timestamp, '%F') as date
  agg count() as scans,
      sum($d.totalIssues) as total_issues,
      sum($d.criticalIssues) as critical_issues
| sortby scans desc
| limit 5000"""

payload = json.dumps({
    "query": QUERY,
    "metadata": {"startDate": start_time, "endDate": end_time, "defaultSource": "logs", "tier": "TIER_ARCHIVE"}
}).encode("utf-8")

req = urllib.request.Request(ENDPOINT, data=payload,
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json",
             "Accept": "application/json", "User-Agent": "Mozilla/5.0 (compatible; CoralogixClient/1.0)"},
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

print(f"Got {len(rows)} rows")
normalized = []
for r in rows:
    email = r.get("email") or r.get("$d.email")
    sa_id = r.get("serviceAccountId") or r.get("$d.serviceAccountId")
    # date from formatTimestamp('%F') is "YYYY-MM-DD"
    date = r.get("date") or None
    normalized.append({
        "tenantName":      r.get("tenantName", ""),
        "email":           email if email and str(email).lower() not in ("null","none","") else None,
        "serviceAccountId": sa_id if sa_id and str(sa_id).lower() not in ("null","none","") else None,
        "sdkType":         r.get("sdkType", ""),
        "sdkVariant":      r.get("sdkVariant"),
        "sdkVersion":      r.get("sdkVersion", ""),
        "platformName":    r.get("platformName", ""),
        "date":            date,
        "scans":           int(r.get("scans") or 0),
        "total_issues":    int(r.get("total_issues") or 0),
        "critical_issues": int(r.get("critical_issues") or 0),
    })

sdk = [r for r in normalized if r["sdkType"] != "MFA"]
mfa = [r for r in normalized if r["sdkType"] == "MFA"]
print(f"SDK rows: {len(sdk)}, with email: {sum(1 for r in sdk if r['email'])}, with SA: {sum(1 for r in sdk if r['serviceAccountId'])}")
print(f"MFA rows: {len(mfa)}, with email: {sum(1 for r in mfa if r['email'])}, with SA: {sum(1 for r in mfa if r['serviceAccountId'])}")

out = os.path.join(BASE, "rows_with_sa.json")
with open(out, "w") as f:
    json.dump(normalized, f)
print(f"Saved to {out}")
