"""Look up the addresses in the 132 legitimate notices on VirusTotal to build the stage 4 evidence snapshot.

Same rules as the original 20-notice snapshot (vt_snapshot.json):
- IP ranges (CIDR): VT has no range lookup, so the first address of the range is queried and this is stated in the evidence.
- Wildcards (*.x.com) and per-customer placeholders (<org>.x.com, PROJECT_ID.x.com): the parent domain is queried and this is stated.
- IPv6 ranges are not queried (they do not appear in the evidence).
Free-key limits (4/min, 500/day) -> 16-second interval. Results accumulate in vt_legit_cache.json, so runs can be resumed.
Stops when the quota is exceeded; running again after the daily quota reset (00:00 UTC) resumes the lookups.

Input: ../data/legit_all.jsonl   Output: vt_snapshot_legit132.json
"""
import ipaddress
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent.parent / "stage2_judge" / ".env")
KEY = os.environ["VT_API_KEY"]
CACHE = HERE / "vt_legit_cache.json"
OLD = json.loads((HERE / "vt_snapshot.json").read_text())
OUT = HERE / "vt_snapshot_legit132.json"
GAP = 16
FILE_EXT = {"md", "yaml", "yml", "json", "key", "txt", "sh", "py", "js", "ts", "html", "htm", "xml", "toml",
            "cfg", "conf", "lock", "ini", "env", "gpg", "asc", "pem", "crt", "tar", "gz", "zip", "deb", "rpm", "exe",
            "php", "aspx", "asp", "jsp", "cgi", "pl", "rb", "go", "java", "cs", "sql", "csv", "pdf", "png", "svg"}
HOST = re.compile(r"(\*\.[a-z0-9.-]+|<[A-Za-z_]+>[.-][a-z0-9.-]+|[A-Z_]{3,}\.[a-z0-9.-]+|(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?|(?:[a-z0-9-]+\.)+[a-z]{2,})")


def lookup_key(shown):
    """Address shown in evidence -> (VT lookup target, kind, substitution note)"""
    if re.match(r"^(?:\d{1,3}\.){3}\d{1,3}/32$", shown):  # /32 is a single IP
        return shown[:-3], "ip", ""
    if re.match(r"^(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}$", shown):
        net = ipaddress.ip_network(shown, strict=False)
        return str(net.network_address), "ip", "range; VirusTotal has no range lookup, first address of the range queried"
    if re.match(r"^(?:\d{1,3}\.){3}\d{1,3}$", shown):
        return shown, "ip", ""
    low = shown.lower()
    if low.startswith("*."):
        return low[2:], "domain", "wildcard; parent domain queried"
    if shown.startswith("<") or re.match(r"^[A-Z_]{3,}\.", shown):
        return low.split(".", 1)[1], "domain", "per-customer subdomain placeholder; parent domain queried"
    return low, "domain", ""


cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
last = [0.0]


def vt(kind, value):
    if f"{kind}:{value}" in cache:
        return cache[f"{kind}:{value}"]
    old = OLD["entries"].get(value)
    if old:  # addresses in the original 20-notice snapshot reuse those values (looked up 2026-09-25)
        cache[f"{kind}:{value}"] = {"stats": {k: old[k] for k in ("malicious", "suspicious", "undetected", "harmless")},
                                    "queried_at": OLD["queried_at"]}
        return cache[f"{kind}:{value}"]
    wait = GAP - (time.time() - last[0])
    if wait > 0:
        time.sleep(wait)
    path = "ip_addresses" if kind == "ip" else "domains"
    r = requests.get(f"https://www.virustotal.com/api/v3/{path}/{value}", headers={"x-apikey": KEY}, timeout=30)
    last[0] = time.time()
    if r.status_code == 429:
        sys.exit("VT quota exceeded - run again after the daily quota reset (00:00 UTC) to resume.")
    if r.status_code == 400:  # not an address (file name, etc.) -> skip and record
        cache[f"{kind}:{value}"] = {"stats": None, "invalid": True, "queried_at": datetime.now(timezone.utc).isoformat()}
        CACHE.write_text(json.dumps(cache, indent=1))
        return cache[f"{kind}:{value}"]
    if r.status_code not in (200, 404):
        r.raise_for_status()
    stats = None if r.status_code == 404 else r.json()["data"]["attributes"].get("last_analysis_stats")
    cache[f"{kind}:{value}"] = {"stats": stats, "queried_at": datetime.now(timezone.utc).isoformat()}
    CACHE.write_text(json.dumps(cache, indent=1))
    return cache[f"{kind}:{value}"]


def main():
    recs = [json.loads(l) for l in (HERE.parent / "data" / "legit_all.jsonl").read_text().splitlines() if l.strip()]
    shown_all = []
    for r in recs:
        for h in [m.group(1) for m in HOST.finditer(r["content"])] + r.get("hosts", []):
            h = h.strip().rstrip(".")
            if ":" in h or h.rsplit(".", 1)[-1].lower() in FILE_EXT or h in shown_all:
                continue
            shown_all.append(h)
    entries, aliases = {}, {}
    for i, shown in enumerate(shown_all, 1):
        key, kind, note = lookup_key(shown)
        res = vt(kind, key)
        if res.get("invalid"):
            print(f"[{i}/{len(shown_all)}] {shown} -> not an address, skipped", flush=True)
            continue
        s = res["stats"] or {}
        entries[key] = {"type": kind, "malicious": s.get("malicious", 0), "suspicious": s.get("suspicious", 0),
                        "undetected": s.get("undetected", 0), "harmless": s.get("harmless", 0),
                        "vt_record": res["stats"] is not None, "queried_at": res["queried_at"][:10]}
        if key != shown.lower() or note:
            aliases[shown] = {"key": key, "note": note}
        print(f"[{i}/{len(shown_all)}] {shown} -> {key}", flush=True)
    OUT.write_text(json.dumps({"source": "VirusTotal (last_analysis_stats), queried via API v3",
                               "queried_at": "2026-09-25~27 (per entry)", "entries": entries, "aliases": aliases},
                              indent=1, ensure_ascii=False))
    print("done", len(entries))


if __name__ == "__main__":
    main()
