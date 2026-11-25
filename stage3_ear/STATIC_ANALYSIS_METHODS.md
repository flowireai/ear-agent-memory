# External analysis techniques that can be plugged into EAR

> In the experiment (Stage 3), **the only thing measured was the VirusTotal reputation lookup**. To keep the metric objective, the basis for judgment was limited to VT.
> The techniques below are external analyses that fit directly into the EAR structure; the experimental results are therefore a **lower bound** on EAR performance.
> All of these techniques share one property: they read external state outside the memory text (which a judge-style checker cannot access).

## 1. Reputation / Threat Intelligence — measured in the experiment
| Method | What it examines | Concrete means |
|---|---|---|
| Multi-engine reputation | Per-engine verdict counts for an IP, domain, URL, or file hash | `last_analysis_stats` from VirusTotal API v3 `/ip_addresses/{ip}`, `/domains/{d}`, `/urls/{id}`, `/files/{hash}` |
| Blocklist lookup | Whether it is listed on known-malicious lists | abuse.ch URLhaus / ThreatFox, Spamhaus DROP/DBL, AbuseIPDB |
| Threat-report IoC matching | Whether it matches attack indicators published in public reports | Vendor report IoC lists, MISP / OpenCTI feeds, STIX/TAXII ingestion |
- Limitation: a verdict appears only after reports accumulate (a gap right after registration). → The static analyses below fill that gap.

## 2. Registration / Ownership
| Method | What it examines | Concrete means |
|---|---|---|
| Domain WHOIS/RDAP | Creation date (newly registered or not), expiry date, registrar, recent ownership transfer or registrar change | `events` (registration, last changed, transfer) from RDAP `https://rdap.org/domain/{d}` |
| IP block owner | Registered organization and allocation date of the IP block | `name`, `entities`, `events` from RIR RDAP `https://rdap.org/ip/{ip}` (ARIN, RIPE, APNIC, etc.) |
| AS number | The network operator the IP belongs to | Team Cymru IP→ASN, RIPEstat `prefix-overview`, `whois -h whois.radb.net` |
- Example: avsvmcloud.com — registered in 2018, dormant for two years, ownership transferred in 2020-02 (based on public reports).

## 3. Certificate
| Method | What it examines | Concrete means |
|---|---|---|
| Certificate Transparency (CT) logs | The domain's first certificate issuance date (whether the infrastructure was recently created) and issuance history | `not_before`, `issuer_name` from crt.sh `https://crt.sh/?q={domain}&output=json` |
| Certificate contents | Subject organization (O=), co-listed domains (SAN), validation level (DV/OV/EV) | `openssl s_client -connect {host}:443 -servername {host}` followed by `openssl x509 -noout -subject -ext subjectAltName` |
| Relationship to the original service | Whether the new address's certificate shares the same organization / SAN as the original service domain | Compare the two results above against the previous address's certificate |

## 4. Infrastructure Relationship
| Method | What it examines | Concrete means |
|---|---|---|
| DNS lookup | Currently resolved IPs, name servers, MX | `dig +short A/AAAA/NS {domain}` |
| Comparison with the previous address | Whether the new address shares the IP block, ASN, name servers, and hosting provider of the previous address | Cross-check the results of sections 2 and 4 against the previous address |
| DNS history (passive DNS) | Past resolution records, recent hosting changes, other domains using the same IP | VirusTotal `/domains/{d}/resolutions`, SecurityTrails, CIRCL Passive DNS |
| Popularity | Whether the domain is widely used | Rank in the Tranco top list |

## 5. Canonical Source Cross-check — skill Tier 2
| Method | What it examines | Concrete means |
|---|---|---|
| Official docs / change history | Whether the original service's official domain carries a notice of the migration | Official docs, changelog, status page, official API specification |
| Package registry metadata | Whether the package name, publisher, and repository URL match | PyPI JSON API, npm registry, crates.io |

## 6. Live System Cross-check — skill Tier 1
| Method | What it examines | Concrete means |
|---|---|---|
| Reference check | Whether the address in memory appears in the actual code, configuration, or lockfiles | `grep -rn` over the repository, config files, `.env.example`, lockfile |
| Allowlist check | Whether the destination is on the organization's egress allowlist / proxy configuration | Firewall / proxy policy, service mesh configuration |

## 7. Dynamic Analysis
| Method | What it examines | Concrete means |
|---|---|---|
| URL sandbox | Response on access, redirect chain, downloaded files, whether it is a phishing page | urlscan.io, VirusTotal URL scan, isolated headless browser |
| File sandbox | Behavior of downloaded executables | Cuckoo/CAPE, commercial sandboxes |
- Limitation: an attacker may detect the sandbox and return a benign response (cloaking).
