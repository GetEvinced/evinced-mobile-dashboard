#!/usr/bin/env python3
"""
Evinced Mobile Dashboard — Full Refresh
Fetches data from BigQuery, rebuilds HTML dashboard, renders PDF.

Run from the evinced-dashboard folder:
    python3 refresh_all.py

Prerequisites:
    pip3 install google-cloud-bigquery playwright --break-system-packages
    python3 -m playwright install chromium
    gcloud auth application-default login
"""
import subprocess, sys, os, json, urllib.request, urllib.error, urllib.parse
from dotenv import load_dotenv

load_dotenv()

BASE = os.path.dirname(os.path.abspath(__file__))

STEPS = [
    ("Fetching scan data from BigQuery",   os.path.join(BASE, "fetch_with_sa.py")),
    ("Fetching latest scan dates from BQ", os.path.join(BASE, "fetch_latest_scan_dates.py")),
    ("Fetching Zendesk tickets",           os.path.join(BASE, "fetch_zendesk.py")),
    ("Rebuilding HTML dashboard",          os.path.join(BASE, "rebuild_dashboard_v5.py")),
    ("Rendering PDF",                      os.path.join(BASE, "render_pdf.py")),
]

def run_step(label, script):
    print(f"\n{'='*60}")
    print(f"▶  {label}")
    print(f"{'='*60}")
    result = subprocess.run([sys.executable, script], capture_output=False)
    if result.returncode != 0:
        print(f"❌  {label} FAILED (exit {result.returncode})")
        sys.exit(result.returncode)
    print(f"✅  {label} done")

def upload_pdf_to_slack(pdf_path):
    token = os.getenv("SLACK_BOT_TOKEN")
    channel = os.getenv("SLACK_CHANNEL_ID", "")
    if not token:
        print("⚠️  SLACK_BOT_TOKEN not set — skipping Slack upload")
        return
    if not channel:
        print("⚠️  SLACK_CHANNEL_ID not set — skipping Slack upload")
        return

    file_size = os.path.getsize(pdf_path)
    file_name = os.path.basename(pdf_path)

    # Step 1: get upload URL
    params = urllib.parse.urlencode({
        "filename": file_name,
        "length": file_size
    })
    req = urllib.request.Request(
        f"https://slack.com/api/files.getUploadURLExternal?{params}",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    if not data.get("ok"):
        print(f"❌  Slack getUploadURLExternal failed: {data}")
        return
    upload_url = data["upload_url"]
    file_id    = data["file_id"]

    # Step 2: PUT file
    with open(pdf_path, "rb") as f:
        content = f.read()
    req2 = urllib.request.Request(upload_url, data=content, method="PUT")
    req2.add_header("Content-Type", "application/pdf")
    with urllib.request.urlopen(req2) as resp2:
        resp2.read()

    # Step 3: complete upload
    payload = json.dumps({
        "files": [{"id": file_id, "title": file_name}],
        "channel_id": channel,
        "initial_comment": "📊 Mobile Products Dashboard — daily refresh"
    }).encode()
    req3 = urllib.request.Request(
        "https://slack.com/api/files.completeUploadExternal",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    )
    with urllib.request.urlopen(req3) as resp3:
        result = json.loads(resp3.read())
    if result.get("ok"):
        print(f"✅  PDF uploaded to Slack channel {channel}")
    else:
        print(f"❌  Slack completeUpload failed: {result}")

if __name__ == "__main__":
    for label, script in STEPS:
        run_step(label, script)

    # Optional: send PDF to Slack
    pdf_path = os.path.join(BASE, "mobile-products-dashboard.pdf")
    if os.path.exists(pdf_path):
        upload_pdf_to_slack(pdf_path)
    else:
        print(f"\n⚠️  PDF not found at {pdf_path} — skipping Slack upload")

    print("\n🎉  All done! Dashboard refreshed.")
