"""Judge the expanded address pairs: aware prompt x (no external evidence / VirusTotal evidence).

Uses the same judge calls, prompt text, and evidence placement (trusted zone) as stage 2 (run_judge) and stage 3 (run_ear_judge).
  python run_expand.py --mode judge --model gpt-5.6-luna
  python run_expand.py --mode ear   --model gpt-5.6-luna
Output: results/<mode>__aware__<model>.jsonl (finished items are skipped; only errored items are retried)
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent / "stage3_ear"))
import run_judge as s2  # noqa: E402
import run_ear_judge as s3  # noqa: E402

DATA = HERE / "data" / "pairs_expanded.jsonl"
RESULTS = HERE / "results"


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["judge", "ear"], required=True)
    ap.add_argument("--model")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    s2.set_model_from_args()
    model = os.environ["JUDGE_MODEL"]
    system = (s2.HERE / "prompts" / "aware.txt").read_text() if args.mode == "judge" else s3.system_prompt("aware")
    RESULTS.mkdir(exist_ok=True)
    out_path = RESULTS / f"{args.mode}__aware__{s2.model_slug(model)}.jsonl"

    entries = [json.loads(l) for l in DATA.read_text().splitlines()]
    for i, e in enumerate(entries):
        e["entry_ref"] = f"mem-{i:04d}"
    done = set()
    if out_path.exists():
        done = {r["id"] for r in map(json.loads, filter(str.strip, out_path.read_text().splitlines())) if not r.get("error")}
    todo = [e for e in entries if e["id"] not in done]
    if args.limit:
        todo = todo[: args.limit]
    print(f"[expand] mode={args.mode} model={model} todo={len(todo)} (done={len(done)}) -> {out_path}")

    if args.mode == "ear":
        orig = s2.user_message
        s2.user_message = lambda e: e["evidence"] + "\n\n" + orig(e)
    llm = s2.build_llm()
    sem = asyncio.Semaphore(int(os.environ.get("JUDGE_CONCURRENCY", "8")))

    async def task(e):
        res = await s2.judge_one(llm, system, e, sem)
        rec = {k: e[k] for k in ("id", "pair_id", "attack", "kind", "addr_pair", "family", "source_model", "run", "label", "ioc")}
        rec.update({"mode": args.mode, "prompt": "aware", "judge_model": model}, **res)
        return rec

    with out_path.open("a") as f:
        for coro in asyncio.as_completed([task(e) for e in todo]):
            f.write(json.dumps(await coro, ensure_ascii=False) + "\n")
            f.flush()


if __name__ == "__main__":
    asyncio.run(main())
