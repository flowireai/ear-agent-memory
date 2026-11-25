# External-Authority Re-Grounding (EAR) for LLM-Agent Memory — Artifacts

Artifact repository for the paper
*"External-Authority Re-Grounding for LLM-Agent Memory: Why Judges Need Outside Evidence to Clean Poisoned Addresses from Memory"*
by Yutai Kim, Seungyeon Han and Changmin Hong (Linearity Corp.), ICISSP 2027.

All attack material is a controlled demonstration. The victim service and the attacker-controlled page host are placeholders
(`api.service-a.example.com`, `attacker.example.org`), and all credentials are canary values. The gateway addresses that the
attacker pages point to are real third-party hosts chosen for their reputation (`45.134.26.41`, `wicar.org`, and a then-clean
unknown domain). Malicious IPs/domains in the expanded pairs are public indicators from the ThreatFox feed.

## Layout

| Path | Content |
|---|---|
| `stage1_injection/` | Stage 1 — memory poisoning in an open-source agent harness (Hermes Agent v0.21.3): 5 attacker pages, the agents' own poisoned memory files (`poisoned_samples/`), per-model results, exfiltration demo page |
| `stage2_judge/` | Stage 2 — LLM judge without external evidence: minimal pairs (`data/pairs.jsonl`, 132 pairs), 3 judge prompts (`prompts/`), judge runner, verdicts of 16 judges (`results/`) |
| `stage2_judge/expand/` | Expanded pairs: 50 malicious IPs + 50 malicious domains from ThreatFox (feed snapshot of 2026-09-26, not redistributed; see Data building), counterparts with zero detections or no VirusTotal record, VirusTotal lookups, 300 pairs × 16 judges, VirusTotal re-query of rejected domains |
| `stage3_ear/` | Stage 3 — same judges with VirusTotal evidence (EAR): evidence snapshot, runner, verdicts, list of external analyses EAR can host |
| `stage4_legit_fp/` | Stage 4 — false positives on 132 real migration notices (the 112 newly collected notices carry their vendor source URL; the original 20 cite their source inside the text, except `L08_ghcr`, a generic team migration note; model-written integration notes, VirusTotal evidence, verdicts). `results/` = original 20 summary-form notices, `results_notes132/` = 132 notices in integration-note form |
| `analysis/` | Aggregation script and the full result tables (`RESULTS_ALL.md`); keyword count of top-level-domain mentions in the judges' reasons (`count_tld_mentions.py`) |
| `deployment/` | Anonymized example reports from the live deployment (same poisoned entry, without / with VirusTotal). |

## Judges

Stage 1 covers 18 models. The judge experiments (stages 2–4 and the expanded pairs) use 16 of them:
`qwen3.5:397b` was retired by its hosting provider during the study, and `gemini-3.1-pro` could not complete all
conditions within the provider's daily request quota, so both were excluded as judges (their Stage 1 results and the
memory files they wrote are still used).

## License

- **Code** (`.py` files): MIT License, see [`LICENSE`](LICENSE).
- **Data and all other files**: CC BY-NC 4.0 (non-commercial use with attribution), see [`LICENSE-DATA`](LICENSE-DATA). Commercial use requires prior written permission from Linearity Corp.
- **Third-party material**: the malicious indicators in the expanded pairs come from ThreatFox by abuse.ch and are subject to the abuse.ch Terms of Use; reputation verdict counts are from VirusTotal and remain subject to its terms.

## Reproducing

Python 3.11+, packages: `langchain-openai langchain-anthropic langchain-google-genai langchain-ollama python-dotenv requests`.
Create `stage2_judge/.env` (not included):

| Variable | Use |
|---|---|
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `OLLAMA_API_KEY` | judge providers (the model name selects the provider: `gpt-*`, `claude-*`, `gemini-*`, otherwise Ollama) |
| `JUDGE_OLLAMA_HOST=https://ollama.com` | Ollama endpoint for open-weight judges |
| `VT_API_KEY` | VirusTotal (only needed to rebuild evidence; all lookups used in the paper are included as caches/snapshots) |
| `JUDGE_MODEL` (optional) | default judge when `--model` is omitted |
| `JUDGE_CONCURRENCY`, `JUDGE_REASONING_EFFORT` (optional) | parallel requests (default 8); OpenAI reasoning effort |

Judging (run from the repository root; each line is independent):

```bash
# Stage 2 / 3 (prompt: aware | loose | tight)
(cd stage2_judge && python run_judge.py --prompt aware --model gpt-5.6-luna)
(cd stage3_ear && python run_ear_judge.py --prompt aware --model gpt-5.6-luna)
# Stage 4 (--set notes132: 132 notices; default: original 20)
(cd stage4_legit_fp && python run_legit.py --set notes132 --mode ear --prompt aware --model gpt-5.6-luna)
# Expanded pairs (--mode judge | ear)
(cd stage2_judge/expand && python run_expand.py --mode ear --model gpt-5.6-luna)
# Aggregate all results
python analysis/summarize_all.py
```

Every runner skips items that already have a verdict and retries only failed ones. The released result files keep
one final record per item. `provider_blocked` marks responses refused by the model provider's safety filter; these are
recorded, not retried, and excluded from the metrics. Records written before this detection was added (the first
gpt-5.6-luna runs) carry no `stop_reason`; no refusals occurred for that provider.

Data building (already done; outputs are included):

| Step | Script | Output |
|---|---|---|
| Stage 2 minimal pairs from Stage 1 memories | `stage2_judge/build_pairs.py` | `stage2_judge/data/pairs.jsonl` |
| Expanded pairs: candidates from the ThreatFox snapshot | `stage2_judge/expand/build_candidates.py` | `candidates.json` |
| VirusTotal check of candidates, zero-detection counterparts | `stage2_judge/expand/vt_pairs.py` | `pairs_expanded.json` (all queried candidates, accepted and rejected, with VT results), `vt_cache.json` |
| Place each address pair in 3 Stage 1 memory contexts | `stage2_judge/expand/build_expanded.py` | `data/pairs_expanded.jsonl` |
| Re-query of rejected domains (~17 h later) | `stage2_judge/expand/requery_rejected.py` | `requery_2026-09-27.json` |
| Legitimate notices → integration notes (7 open-weight models) | `stage4_legit_fp/convert_notes.py` | `data/legit_notes.jsonl`, `legit_notes_fixlog.jsonl` |
| VirusTotal evidence for the notices | `stage4_legit_fp/evidence/vt_legit.py` | `vt_snapshot_legit132.json`, `vt_legit_cache.json` |

Candidate selection for the expanded pairs ran in passes: the IP candidates come from the first pass
(`candidates_v1_ip30d_dom30d.json`, 30-day window), and the domain window was then widened to all of 2026 because many recent
attack domains had fewer than 5 VirusTotal detections. `pairs_expanded.json` is the authoritative record of every candidate
that was queried (including one accepted domain, `costum342183.life`, that came from an intermediate pass whose candidate list was overwritten); re-running `build_candidates.py` overwrites `candidates.json`.

The ThreatFox feed snapshot itself is not redistributed. `build_candidates.py` expects a ThreatFox CSV export (https://threatfox.abuse.ch/export/)
at `stage2_judge/expand/feeds/threatfox.csv`; a current export differs from the 2026-09-26 snapshot, so it will not reproduce the same candidates.
All other steps run without the feed.
