"""Share of no-evidence verdicts on malicious domains whose stated reason mentions the top-level domain (TLD).

Population: expanded pairs, 16 judges, aware prompt, no evidence; malicious domain versions that were blocked
(last record per id).
A reason counts as a mention if it contains "TLD(s)" or "top-level", or the domain's own suffix written on its
own (for example ".icu"); the suffix inside the full domain name does not count. This is a keyword search, so it
shows what the reasons mention, not what caused the verdict.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = ["gpt-6-astra", "gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "claude-opus-5", "claude-sonnet-5",
          "claude-haiku-4-5-20251001", "gemini-3.8-flash", "gemini-3.5-flash-lite", "glm-5.3", "kimi-k3",
          "minimax-m3", "deepseek-v4-pro", "nemotron-3-ultra", "gemma4-31b", "mistral-large-3-675b"]
WORD = re.compile(r"\btlds?\b|top[- ]level", re.I)

both = word_only = suffix_only = total = 0
for m in MODELS:
    last = {}
    for line in open(ROOT / f"stage2_judge/expand/results/judge__aware__{m}.jsonl"):
        if line.strip():
            r = json.loads(line)
            last[r["id"]] = r
    for r in last.values():
        if r["label"] != "malicious" or r["verdict"] != "block" or re.match(r"^\d+\.", r["ioc"]):
            continue
        total += 1
        suffix = re.escape(r["ioc"].rsplit(".", 1)[1])
        w = bool(WORD.search(r["reasoning"]))
        s = bool(re.search(r"(?<![a-z0-9-])\." + suffix + r"\b", r["reasoning"], re.I))
        both += w and s
        word_only += w and not s
        suffix_only += s and not w

n = both + word_only + suffix_only
print(f"blocked malicious-domain verdicts: {total}")
print(f"mention the TLD: {n} ({100 * n / total:.1f}%)  [both {both}, word only {word_only}, suffix only {suffix_only}]")
