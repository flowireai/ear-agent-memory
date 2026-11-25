"""Re-query the 41 attack domains rejected in expanded-pair selection for 'fewer than 5 VT malicious verdicts' and record verdict changes.
Compared with the first lookup (2026-09-26, rejected[].vt in pairs_expanded.json). Output: requery_<date>.json
Run: python requery_rejected.py  (VT_API_KEY; 16-second interval)
"""
import json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
import requests
from dotenv import load_dotenv
HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")
KEY = os.environ["VT_API_KEY"]
rej = [r for r in json.loads((HERE / "pairs_expanded.json").read_text())["rejected"] if r["kind"] == "domain" and r["reason"].startswith("VT malicious")]
out_path = HERE / f"requery_{datetime.now().strftime('%Y-%m-%d')}.json"
out = json.loads(out_path.read_text()) if out_path.exists() else {}
for r in rej:
    d = r["ioc"]
    if d in out:
        continue
    resp = requests.get(f"https://www.virustotal.com/api/v3/domains/{d}", headers={"x-apikey": KEY}, timeout=30)
    if resp.status_code == 429:
        sys.exit("VT quota exceeded")
    stats = resp.json()["data"]["attributes"].get("last_analysis_stats") if resp.status_code == 200 else None
    before = (r["vt"]["stats"] or {}).get("malicious", 0)
    after = (stats or {}).get("malicious", 0)
    out[d] = {"family": r["family"], "first_seen": r["first_seen"], "before": r["vt"], "after": {"stats": stats, "queried_at": datetime.now(timezone.utc).isoformat()}, "delta_malicious": after - before}
    out_path.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"{d}: {before} -> {after}", flush=True)
    time.sleep(16)
print("done", len(out))
