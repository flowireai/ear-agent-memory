"""Expanded address pairs, step 2: confirm maliciousness with VirusTotal + find a counterpart address.

- Malicious address: accepted only with at least 5 VT malicious verdicts
- Counterpart IP: change the last octet by ±1, ±2, ... and take the first address with 0 VT malicious and 0 suspicious
- Counterpart domain: change only the TLD (.com -> .net -> .org ...) and take the first domain with 0 VT malicious and 0 suspicious, or with no VT record.
  Zero detections means "no verdict", not "safe", so we also record whether VT knows the domain (harmless+undetected count)
  and whether it resolves in DNS.
- 16-second interval to fit the free-key limits (4/min, 500/day). Lookups accumulate in vt_cache.json, so runs can be resumed.
- Stops once the targets (50 IPs, 50 domains) are met. All rejection reasons are recorded.

Key: VT_API_KEY in stage2_judge/.env
Output: pairs_expanded.json, vt_cache.json (with lookup timestamps)
"""
import json
import os
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")
KEY = os.environ.get("VT_API_KEY")
CACHE = HERE / "vt_cache.json"
OUT = HERE / "pairs_expanded.json"
TARGET = 50
MIN_MAL = 5
GAP = 16  # seconds
IP_OFFSETS = [1, -1, 2, -2, 3, -3, 4, -4, 5, -5]
TLD_SWAP = ["com", "net", "org", "io", "co", "info"]

cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
last_call = [0.0]


def vt(kind: str, value: str) -> dict:
    ck = f"{kind}:{value}"
    if ck in cache:
        return cache[ck]
    wait = GAP - (time.time() - last_call[0])
    if wait > 0:
        time.sleep(wait)
    path = "ip_addresses" if kind == "ip" else "domains"
    r = requests.get(f"https://www.virustotal.com/api/v3/{path}/{value}",
                     headers={"x-apikey": KEY}, timeout=30)
    last_call[0] = time.time()
    if r.status_code == 429:
        sys.exit("VT quota exceeded - run again tomorrow to resume.")
    if r.status_code == 404:
        stats = None
    else:
        r.raise_for_status()
        stats = r.json()["data"]["attributes"].get("last_analysis_stats")
    cache[ck] = {"stats": stats, "queried_at": datetime.now(timezone.utc).isoformat()}
    CACHE.write_text(json.dumps(cache, indent=1))
    return cache[ck]


def mal(res):
    s = res["stats"]
    return (s or {}).get("malicious", 0), (s or {}).get("suspicious", 0)


def resolves(host):
    try:
        socket.getaddrinfo(host, None)
        return True
    except OSError:
        return False


def ip_variants(ip):
    a, b, c, d = map(int, ip.split("."))
    for o in IP_OFFSETS:
        if 1 <= d + o <= 254:
            yield f"{a}.{b}.{c}.{d + o}"


def dom_variants(dom):
    name, tld = dom.rsplit(".", 1)
    for t in TLD_SWAP:
        if t != tld:
            yield f"{name}.{t}"


def main():
    if not KEY:
        sys.exit("Please set VT_API_KEY in stage2_judge/.env.")
    cands = json.loads((HERE / "candidates.json").read_text())
    out = json.loads(OUT.read_text()) if OUT.exists() else {"ip": [], "domain": [], "rejected": []}
    done = {p["malicious"] for k in ("ip", "domain") for p in out[k]} | {r["ioc"] for r in out["rejected"]}
    for kind, variants in (("ip", ip_variants), ("domain", dom_variants)):
        for c in cands[kind]:
            if len(out[kind]) >= TARGET:
                break
            if c["ioc"] in done:
                continue
            m = vt(kind, c["ioc"])
            if mal(m)[0] < MIN_MAL:
                out["rejected"].append({**c, "kind": kind, "reason": f"VT malicious {mal(m)[0]} < {MIN_MAL}", "vt": m})
            else:
                pair = None
                for v in variants(c["ioc"]):
                    b = vt(kind, v)
                    # IP: known to VT with 0 detections. Domain: TLD-swapped domains often have no VT record, so
                    # "no record" is also accepted (both are "no evidence" to the judge). Which case applies is kept in benign_known_to_vt.
                    if (b["stats"] is None and kind == "domain") or (b["stats"] is not None and mal(b) == (0, 0)):
                        pair = v
                        break
                if pair is None:
                    out["rejected"].append({**c, "kind": kind, "reason": "no zero-detection counterpart found", "vt": m})
                else:
                    s = cache[f"{kind}:{pair}"]["stats"] or {}
                    out[kind].append({**c, "malicious": c["ioc"], "benign": pair, "vt_malicious": m,
                                      "vt_benign": cache[f"{kind}:{pair}"],
                                      "benign_known_to_vt": s.get("harmless", 0) + s.get("undetected", 0) > 0,
                                      "benign_resolves": resolves(pair) if kind == "domain" else None})
            OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False))
            print(f"[{kind}] accepted {len(out[kind])}/{TARGET}  rejected {len(out['rejected'])}", flush=True)
    print("done")


if __name__ == "__main__":
    main()
