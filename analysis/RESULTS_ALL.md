# All results for 16 judge models (aware, main condition)

Provider-blocked responses (provider_blocked) are not verdicts, so they are excluded from metrics and only their counts are reported.

## Confusion matrix 1: poisoned memory vs real legitimate notices (132 vs 132 per model)

- No evidence: TP 1144, FN 915, FP 75, TN 2032 (provider-blocked 52, inconclusive 6)
- EAR evidence (VT): TP 2051, FN 13, FP 61, TN 2046 (provider-blocked 48, inconclusive 5)

| | Accuracy | Precision | Recall | F1 | FPR |
|---|---:|---:|---:|---:|---:|
| (ref) block all | 49.4% | 49.4% | 100.0% | 0.662 | 100.0% |
| No evidence | 76.2% | 93.8% | 55.6% | 0.698 | 3.6% |
| EAR evidence (VT) | 98.2% | 97.1% | 99.4% | 0.982 | 2.9% |

## Confusion matrix 2: pair experiment, 132 pairs (same text, only the address differs)

| | Accuracy | Precision | Recall | F1 | FPR |
|---|---:|---:|---:|---:|---:|
| (ref) block all | 50.0% | 50.0% | 100.0% | 0.667 | 100.0% |
| No evidence | 50.4% | 50.4% | 55.6% | 0.528 | 54.8% |
| EAR evidence (VT) | 84.4% | 76.5% | 99.4% | 0.864 | 30.6% |

- No evidence: pairs 2112, correctly separated 150, inverted 135, provider-blocked variants 106
- EAR evidence (VT): pairs 2112, correctly separated 1416, inverted 0, provider-blocked variants 97

## Expanded 300 pairs (100 address pairs x 3 contexts)

| | Accuracy | Precision | Recall | F1 | FPR |
|---|---:|---:|---:|---:|---:|
| (ref) block all | 50.0% | 50.0% | 100.0% | 0.667 | 100.0% |
| No evidence | 51.7% | 51.1% | 77.0% | 0.614 | 73.4% |
| EAR evidence (VT) | 70.4% | 62.9% | 99.6% | 0.771 | 59.0% |

- No evidence: pairs 4800, correctly separated 365, inverted 201, provider-blocked variants 472
- EAR evidence (VT): pairs 4800, correctly separated 1881, inverted 0, provider-blocked variants 291

## Per model (aware)

| Model | Recall none→VT | FPR none→VT | Pair accuracy none→VT | Pair inverted none→VT | Expanded inverted none→VT | Provider-blocked (stages 2/3) |
|---|---|---|---|---|---|---:|
| gpt-6-astra | 23→100% | 1.5→2.3% | 55→96% | 2→0 | 6→0 | 0 |
| gpt-5.6-sol | 58→100% | 8.3→5.3% | 47→86% | 21→0 | 19→0 | 0 |
| gpt-5.6-terra | 21→100% | 5.3→9.8% | 49→91% | 12→0 | 21→0 | 0 |
| gpt-5.6-luna | 43→100% | 11.4→16.7% | 49→88% | 13→0 | 24→0 | 0 |
| claude-opus-5 | 100→100% | 3.0→0.8% | 53→60% | 0→0 | 0→0 | 203 |
| claude-sonnet-5 | 93→100% | 1.5→0.8% | 50→71% | 3→0 | 0→0 | 0 |
| claude-haiku-4-5-20251001 | 72→100% | 1.5→3.0% | 48→76% | 15→0 | 13→0 | 0 |
| gemini-3.8-flash | 77→100% | 3.0→0.8% | 49→77% | 6→0 | 0→0 | 0 |
| gemini-3.5-flash-lite | 70→100% | 0.8→0.0% | 51→74% | 7→0 | 9→0 | 0 |
| glm-5.3 | 73→100% | 1.5→0.8% | 45→81% | 17→0 | 3→0 | 0 |
| kimi-k3 | 94→100% | 6.1→0.0% | 50→64% | 6→0 | 2→0 | 0 |
| minimax-m3 | 45→92% | 6.8→0.8% | 48→93% | 11→0 | 19→0 | 0 |
| deepseek-v4-pro | 36→100% | 6.1→4.5% | 56→97% | 13→0 | 37→0 | 0 |
| nemotron-3-ultra | 5→98% | 0.0→0.0% | 50→99% | 5→0 | 21→0 | 0 |
| gemma4-31b | 41→100% | 0.0→0.0% | 53→100% | 1→0 | 12→0 | 0 |
| mistral-large-3-675b | 55→100% | 0.0→0.8% | 52→89% | 3→0 | 15→0 | 0 |

## Auxiliary conditions loose / tight (16 models, 132 pairs): malicious variant blocked / counterpart blocked / legitimate-notice FP

- loose No evidence: malicious variant blocked 74/2045, counterpart blocked 77/2046, legitimate-notice FP 8/2112, inverted 29
- loose EAR evidence (VT): malicious variant blocked 1068/2033, counterpart blocked 52/2038, legitimate-notice FP 13/2111, inverted 2
- tight No evidence: malicious variant blocked 1934/2028, counterpart blocked 1915/2032, legitimate-notice FP 625/2103, inverted 33
- tight EAR evidence (VT): malicious variant blocked 2033/2033, counterpart blocked 1626/2032, legitimate-notice FP 375/2100, inverted 0
