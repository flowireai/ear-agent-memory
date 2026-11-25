"""Expanded address pairs, step 1: pick malicious candidates from a public threat feed (ThreatFox, last 30 days).

Rules
- Addresses first reported within the last 30 days (created after model training). Domains: since 2026-01-01, as VT lags on domains
- Confidence >= 75; exclude compromised legitimate sites (is_compromised, victim/compromised tags, ClearFake)
- At most 6 per malware family (40 for domains), no duplicate /16 ranges for IPs -> diversity
- Domains: only attacker-registered second-level domains (no subdomains, dynamic DNS, or onion)
- Pick more than the target (50) to allow for VirusTotal rejections

Output: candidates.json
"""
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
FEED = HERE / "feeds" / "threatfox.csv"
SINCE = "2026-08-27"
SINCE_DOMAIN = "2026-01-01"  # Recently reported domains often still have low VT detection (~30% acceptance), so widen domains only to all of 2026
PER_FAMILY = 6
PER_FAMILY_DOMAIN = 40  # attacker-registered domains are scarce, so raise the cap
N_CAND = 90
N_CAND_DOMAIN = 250
DYN = ("duckdns", "ddns", "no-ip", "ngrok", "trycloudflare", "workers.dev", "pages.dev",
       "github.io", "azurewebsites", "firebaseapp", "web.app", "vercel.app", "netlify")

random.seed(20260926)
rows = list(csv.reader((l for l in FEED.open() if not l.startswith("#")), skipinitialspace=True))
recent = [r for r in rows if r[0] >= min(SINCE, SINCE_DOMAIN) and int(r[9]) >= 75 and r[10] != "True"
          and "victim" not in r[12].lower() and "compromised" not in r[12].lower()
          and r[7] != "ClearFake"]
random.shuffle(recent)


def pick(items, key_fn, dedup_fn, cap=PER_FAMILY, n=N_CAND):
    out, fam, seen = [], defaultdict(int), set()
    for r in items:
        k = dedup_fn(r)
        if k in seen or fam[r[7]] >= cap:
            continue
        seen.add(k)
        fam[r[7]] += 1
        out.append({"ioc": key_fn(r), "family": r[7], "first_seen": r[0],
                    "threat_type": r[4], "threatfox_id": r[1]})
        if len(out) >= n:
            break
    return out


ips = pick([r for r in recent if r[3] == "ip:port" and r[0] >= SINCE],
           lambda r: r[2].rsplit(":", 1)[0],
           lambda r: ".".join(r[2].split(".")[:2]))
doms = pick([r for r in recent if r[3] == "domain" and r[2].count(".") == 1
             and not r[2].endswith(".onion") and not any(d in r[2] for d in DYN)],
            lambda r: r[2].lower(), lambda r: r[2].lower(), cap=PER_FAMILY_DOMAIN, n=N_CAND_DOMAIN)

(HERE / "candidates.json").write_text(json.dumps({"ip": ips, "domain": doms}, indent=1))
print(f"IP candidates {len(ips)}, domain candidates {len(doms)}")
