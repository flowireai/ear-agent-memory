"""Stage 4: measure false positives on real vendor migration notices (default: the original 20 summary-form notices; --set notes132: 132 notices in integration-note form).

Uses the same judges and prompts as stages 2/3 and measures two conditions: judge only (--mode judge) / judge + EAR (--mode ear).
These memories are legitimate, so every block is a false positive.
  python run_legit.py --mode ear --prompt aware
"""
import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "stage2_judge"))
sys.path.insert(0, str(ROOT / "stage3_ear"))
import run_judge as s2  # noqa: E402
import run_ear_judge as s3  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / "stage2_judge" / ".env")
# --set notes132: 132 legitimate notices (converted by models to integration-note format, 2026-09-27) / default: original 20 in summary format
NOTES132 = "--set" in sys.argv and sys.argv[sys.argv.index("--set") + 1] == "notes132"
# The snapshot is needed only for the "judge + VT" (ear) condition. So that the judge condition can run before VT lookups finish, it falls back to empty evidence.
_SNAP_PATH = HERE / "evidence" / ("vt_snapshot_legit132.json" if NOTES132 else "vt_snapshot.json")
EAR_MODE = "--mode" in sys.argv and sys.argv[sys.argv.index("--mode") + 1] == "ear"
if EAR_MODE and not _SNAP_PATH.exists():
    raise SystemExit(f"VT snapshot not found: {_SNAP_PATH}")
SNAP = json.loads(_SNAP_PATH.read_text()) if _SNAP_PATH.exists() else {"queried_at": "", "entries": {}, "aliases": {}}
DATA = HERE / "data" / ("legit_notes.jsonl" if NOTES132 else "legit.jsonl")
RESULTS_DIR = HERE / ("results_notes132" if NOTES132 else "results")
HOST = re.compile(r"(\*\.[a-z0-9.-]+|<[a-z_]+>[.-][a-z0-9.-]+|[A-Z_]{3,}\.[a-z0-9.-]+|(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?|(?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)


def evidence_for(content: str) -> str:
    lines = [f"EXTERNAL EVIDENCE (trusted tool output, VirusTotal engine verdict counts, queried "
             f"{SNAP['queried_at']}, reported as-is):"]
    seen = []
    for m in HOST.finditer(content):
        shown = m.group(1)
        alias = SNAP["aliases"].get(shown)
        key = alias["key"] if alias else shown.lower()
        if key not in SNAP["entries"] or shown in seen:
            continue
        seen.append(shown)
        e = SNAP["entries"][key]
        note = f" [{alias['note']}: {key}]" if alias and alias["note"] else ""
        if e.get("vt_record") is False:  # address with no VT record (same notation as the expanded experiment)
            lines.append(f"- {shown} ({e['type']}){note}: no record in VirusTotal")
            continue
        lines.append(f"- {shown} ({e['type']}){note}: malicious {e['malicious']}, suspicious {e['suspicious']}, "
                     f"undetected {e['undetected']}, harmless {e['harmless']}")
    if not seen:
        lines.append("- (no network destination found in this entry)")
    return "\n".join(lines)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["judge", "ear"], required=True)
    ap.add_argument("--prompt", choices=["loose", "aware", "tight"], required=True)
    ap.add_argument("--model", help="judge model (instead of JUDGE_MODEL in .env)")
    ap.add_argument("--set", choices=["orig20", "notes132"], default="orig20")
    args = ap.parse_args()
    s2.set_model_from_args()
    model = os.environ["JUDGE_MODEL"]
    base = (ROOT / "stage2_judge" / "prompts" / f"{args.prompt}.txt").read_text()
    system = base if args.mode == "judge" else s3.system_prompt(args.prompt)
    RESULTS_DIR.mkdir(exist_ok=True)
    out_path = RESULTS_DIR / f"{args.mode}__{args.prompt}__{s2.model_slug(model)}.jsonl"
    entries = [json.loads(l) for l in DATA.read_text().splitlines()]
    for i, e in enumerate(entries):
        e["entry_ref"] = f"mem-{i:04d}"
        e["evidence"] = evidence_for(e["content"])
    done = set()
    if out_path.exists():
        # Items that ended in errors (rate limit, timeout, etc.) are not treated as done and are retried. Aggregation uses the last record per id.
        done = {r["id"] for r in map(json.loads, filter(str.strip, out_path.read_text().splitlines())) if not r.get("error")}
    todo = [e for e in entries if e["id"] not in done]
    if args.mode == "ear":
        orig = s2.user_message
        s2.user_message = lambda e: e["evidence"] + "\n\n" + orig(e)
    llm = s2.build_llm()
    sem = asyncio.Semaphore(int(os.environ.get("JUDGE_CONCURRENCY", "8")))

    async def task(e):
        res = await s2.judge_one(llm, system, e, sem)
        rec = {"id": e["id"], "label": "benign", "mode": args.mode, "prompt": args.prompt, "judge_model": model}
        if args.mode == "ear":
            rec["evidence"] = e["evidence"]
        rec.update(res)
        return rec

    with out_path.open("a") as f:
        for coro in asyncio.as_completed([task(e) for e in todo]):
            f.write(json.dumps(await coro, ensure_ascii=False) + "\n")
    rows = list({r["id"]: r for r in map(json.loads, filter(str.strip, out_path.read_text().splitlines()))}.values())  # last record per id
    blocked = sorted(r["id"] for r in rows if r["verdict"] == "block")
    print(f"{args.mode:5s} {args.prompt:5s}: FP (block) {len(blocked)}/{len(rows)} {blocked}")


if __name__ == "__main__":
    asyncio.run(main())
