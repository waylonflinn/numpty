---
id: decision-002
title: >-
  Winnow-12B is served by upstream llama-server through metadata-only conversion
  (type nimble); Winnow for text accuracy, Clef-Flash for images, calibration,
  and throughput
date: '2026-10-07 19:53'
status: accepted
---
## Context

NUMP-018 asked how to serve a Jev-style model that ships without llama.cpp decision metadata on upstream llama-server, Winnow-12B first. decision-001 recommends Clef-Flash Q8_0 as the local decision model and lev Q8_0 as the small alternative. Winnow-12B (Gemma-4-12B-it LoRA merged, Apache-2.0, JevBench v1.6.1 Capability 71.2, rank 8) ran only on the author's llama.cpp fork. The user plans to fine-tune Jev-like models of their own and serve them on llama.cpp, so the conversion path matters as much as this model.

doc-007 holds the findings. The fork reads letter logits at the last prompt token over single-token labels A..Z, AA..ZZ, noul false first, one temperature 1.0. That is upstream type `nimble`. A copy of the published Q8_0 GGUF with five added header keys (`gemma4.decision.type = nimble`, three temperature keys, a `systemone` template) runs on upstream b11429. The rendered prompt equals the fork's text. One tokenizer boundary differs by one token, and no template can remove it.

Routes considered: metadata-only conversion (chosen), the author's fork (a pinned old llama.cpp with eight patches, its own endpoint, a second server to run), and an upstream PR for a new type or for image input on `nimble` (not needed for text, tracked as NUMP-020).

### Winnow against Clef-Flash

Measured on saturn, RTX 3090, Q8_0 weights, q8_0 KV, through the router (doc-007, doc-005). Bold marks the better value.

| criterion | Winnow-12B (nimble) | Clef-Flash-9B | prefer |
|---|---|---|---|
| JevBench public, correct of 231 | **198** | 190 | Winnow |
| JevBench Brier | **0.205** | 0.235 | Winnow |
| JevBench ordinal MAE | **0.189** | 0.243 | Winnow |
| typed-decisions accuracy (2,000 decisions) | 0.702 | **0.707** | tie |
| typed-decisions score accuracy | **0.671** | 0.620 | Winnow |
| typed-decisions choice accuracy | 0.657 | **0.710** | Clef-Flash |
| typed-decisions noul accuracy | 0.788 | **0.818** | Clef-Flash |
| calibration: JevBench ECE | 0.067 | **0.058** | Clef-Flash |
| calibration: typed-decisions KL from gold | 0.629 | **0.209** | Clef-Flash |
| calibration: typed-decisions Brier | 0.238 (uniform baseline) | **0.110** | Clef-Flash |
| image input | no, server returns 501 for `nimble` | **yes** | Clef-Flash |
| one question, warm, JevBench p95 | 0.92 s | **0.67 s** | Clef-Flash |
| five questions on one state, warm p50 | 0.79 s, 1,721 input tokens | **0.37 s, 868 tokens** | Clef-Flash |
| VRAM at 8k context | **13.1 GB** | 13.5 GB plus 3 GB batch at 16k | Winnow |
| license | Apache-2.0 | Apache-2.0 | tie |

#### Throughput

Winnow answers each question in its own prompt. Clef-Flash answers all questions on one state in one prompt. So the gap grows with the number of questions per state. Warm medians on saturn, 2026-10-08, first test case of each typed-decisions workflow, prefix cached, one request at a time:

| case | Winnow | Clef-Flash | Clef-Flash time saved | Clef-Flash throughput |
|---|---|---|---|---|
| one question | 0.22 s | 0.20 s | 9% | 1.1x |
| one question, JevBench p95 (doc-007) | 0.92 s | 0.67 s | 27% | 1.4x |
| five questions on one state | 0.79 s | 0.36 s | 54% | 2.2x |
| five questions, input tokens | 1,664 | 856 | 49% | |

The typed-decisions run in doc-007 (400 cases, states not repeated) gives the same five-question figures: 0.79 s against 0.37 s. One question per request is a near tie. Five questions per request cost Winnow twice the time and twice the tokens, and the ratio grows with more questions.

#### Calibration

Winnow puts most of the probability mass on one option: mean p_max 0.858 for 0.702 agreement with the teacher on typed-decisions. Clef-Flash's mean p_max is 0.703 for 0.707 agreement, so its confidence matches its accuracy on that data. Example distributions from the same run, options in the order of the question's criteria. Bold marks the gold label's column.

| question | teacher (gold) | Clef-Flash | Winnow |
|---|---|---|---|
| agent trace, `risk` (score, 4 levels, label 1) | [0.30, **0.62**, 0.08, 0.01] | [0.21, **0.64**, 0.07, 0.08] | [0.02, **0.95**, 0.01, 0.02] |
| customer service, `churn_risk` (score, 4 levels, label 1) | [0.10, **0.73**, 0.17, 0.00] | [0.09, **0.72**, 0.11, 0.08] | [0.02, **0.95**, 0.03, 0.00] |
| security incident, `credential_compromise` (noul, label true) | [0.30, **0.70**] | [0.26, **0.74**] | [0.09, **0.91**] |
| customer service, `needs_human` (noul, label false) | [**0.53**, 0.47] | [**0.45**, 0.55] | [**0.06**, 0.94] |
| security incident, `severity` (score, 5 levels, label 3) | [0.02, 0.08, 0.37, **0.45**, 0.08] | [0.16, 0.15, 0.37, **0.25**, 0.07] | [0.01, 0.02, 0.06, **0.89**, 0.03] |
| customer service, `category` (choice, 5 options, label delivery) | [0.01, 0.01, **0.92**, 0.05, 0.01] | [0.00, 0.00, **0.73**, 0.14, 0.12] | [0.00, 0.00, **0.99**, 0.00, 0.01] |

Reading: on the first three rows all three agree on the answer, and Clef-Flash reproduces the teacher's spread while Winnow collapses it to one option. On `needs_human` the teacher is split, Clef-Flash is split, and Winnow is certain on the wrong side. On `severity` Winnow is right and sharp where Clef-Flash spreads too far and misses. On `category` the teacher is sharp too, and Winnow is closer to it than Clef-Flash. So Winnow's sharpness is not wrong per se. It is constant, while the teacher's and Clef-Flash's sharpness vary with the case. A client that reads the distribution gets that variation from Clef-Flash and not from Winnow.

The two Brier columns in the table above use different targets. JevBench Brier is against a one-hot label, so it rewards accuracy and sharpness together, and Winnow wins it. typed-decisions Brier and KL are against the teacher's distribution, so they reward matching the spread, and Clef-Flash wins them. ECE on JevBench is the one metric that measures confidence against accuracy alone, and there the two are close (0.067 against 0.058).

## Decision

1. Route: metadata-only conversion. A Jev-style model whose mechanism matches an upstream decision type (openjev, lev, nimble, kev, laya, clef) is converted by adding header keys and a `systemone` template to a copy of the published GGUF, with the recipe in doc-007. No fork and no upstream PR now. A model that needs a new readout (interior answer slots, isolated score levels, a custom head) waits for an upstream type.
2. The recommended local decision model is situational. numpty docs name both models and this rule:

| requirement | model |
|---|---|
| text only, accuracy on choice and score questions is the priority | Winnow-12B Q8_0, converted |
| image input | Clef-Flash Q8_0 |
| calibrated probabilities (a client that reads the distribution, not only the answer) | Clef-Flash Q8_0 |
| throughput, above all several questions on one state | Clef-Flash Q8_0 |
| small footprint | lev Q8_0 |
| offline test fixture | Laya |

   When a request needs one or more of images, calibration, or throughput, Clef-Flash is the choice. Winnow is the choice for text-only requests where accuracy per question is the priority and latency is not.
3. The converted file lives on saturn as `/opt/llama/models/Winnow-12B-Q8_0-systemone.gguf`, preset `winnow-12b-Q8`. The template and copy script are recorded in doc-007, not in the repo.
4. Tolerance for a conversion: rendered prompt text equal to the source renderer, and the published benchmark figure reproduced within one item on JevBench public (or an agreed figure for another benchmark). Winnow met both.

## Consequences

- numpty docs that name Clef-Flash as the only local decision model change to the table above. NUMP-007 keeps final authority over client code. No numpty code changes from this decision.
- The image row changes when NUMP-020 gets image input for `nimble` upstream. Until then Clef-Flash is required for images.
- A fine-tuned Gemma 4 decision model of the user's own needs the same five keys and a template that matches its training prompt. The recipe and the verification steps in doc-007 are the procedure. A single-token label alphabet, a fixed noul order and one prompt per question keep such a model inside type `nimble` or `openjev`.
- Winnow's `confidence` from llama-server uses the TypeSafe formulas, not the fork's inverse entropy. A client that needs calibrated distributions uses Clef-Flash or recalibrates Winnow.
- The one-token boundary difference against the fork is accepted. The parity evidence is the benchmark figure, not per-option probabilities, because the fork was not built (review decision). If a later model misses its figure, build the source fork for per-option comparison as the first troubleshooting step.
- The 64-option training limit is not enforced by the server (nimble allows 255). Clients keep choice questions at 64 options or fewer.
- Cygnet (frozen Gemma-4-12B-it plus the same shim shape) is the cheapest next conversion test. Quyet-1.0-Large needs type openjev and a 31B Q4 that is tight on the 3090. decider-4b converts for choice and noul only.
- doc-006's recurrent watch no longer needs to look for a Winnow decision GGUF.
