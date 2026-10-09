---
id: decision-003
title: >-
  Quyet-1.0-Large (type openjev, Q4_K_M, 32k) replaces Winnow for text accuracy
  and Clef-Flash for images and calibration; Clef-Flash stays for throughput and
  small VRAM
date: '2026-10-08 20:44'
status: proposed
---
## Context

NUMP-022 asked whether Quyet-1.0-Large (Chinh Nguyen, Gemma-4-31B-it LoRA merged, Apache-2.0, first on JevBench v1.6.1 with Capability 81.7 against Winnow's 71.2) can be served by upstream llama-server through the metadata-only conversion of doc-007, and whether it changes the requirement-to-model table of decision-002. decision-002 names Winnow-12B for text accuracy and Clef-Flash for images, calibrated probabilities and throughput. The published GGUF is a plain `gemma4` chat conversion (501 on `/v1/systemone`, doc-005). A 31B model at Q4_K_M is 18.7 GB, so the quant and context were a planning choice (Q4_K_M, 32k target, 16k fallback; review 2026-10-08).

doc-009 holds the findings. The quyet runtime reads letter logits A..J at the last prompt token, noul true first, one per-type temperature, prompt version 2 with the Gemma 4 template and thinking off. That is upstream type `openjev`. A copy of the mradermacher Q4_K_M GGUF with five added header keys runs on b11429; the rendered prompt equals the quyet renderer byte for byte and tokenizes to the same count on 7 varied questions. 32k context fits with q8_0 KV: 21.0 GB, 22.3 GB with the Gemma 4 mmproj, because the 31B has 4 KV heads on its 10 global layers and llama.cpp keeps 1,536 cells for the 50 sliding-window layers. doc-006's 22 GB at 8k estimate averaged the KV heads and is superseded.

### Quyet against Winnow and Clef-Flash

Measured on saturn, RTX 3090, through the router, q8_0 KV, from the Mac, doc-008 protocol, 2026-10-08. Quyet is Q4_K_M; the others are Q8_0. Bold marks the best value.

| criterion | Quyet-1.0-Large (openjev, Q4_K_M) | Winnow-12B (nimble) | Clef-Flash-9B | prefer |
|---|---|---|---|---|
| JevBench public, correct of 231 | **208** | 198 | 190 | Quyet |
| JevBench Brier | **0.139** | 0.205 | 0.235 | Quyet |
| JevBench ECE | **0.043** | 0.067 | 0.058 | Quyet |
| JevBench ordinal MAE | **0.171** | 0.189 | 0.243 | Quyet |
| typed-decisions accuracy (2,000 decisions) | **0.804** | 0.702 | 0.707 | Quyet |
| typed-decisions noul / choice / score accuracy | **0.878 / 0.753 / 0.786** | 0.788 / 0.657 / 0.671 | 0.818 / 0.710 / 0.620 | Quyet |
| calibration: typed-decisions KL from gold | 0.270 | 0.629 | **0.209** | Clef-Flash, Quyet close |
| calibration: typed-decisions Brier | 0.111 | 0.238 | **0.110** | tie |
| calibration: mean p_max against accuracy | 0.797 for 0.804 | 0.858 for 0.702 | 0.703 for 0.707 | Quyet and Clef-Flash |
| image input | yes with the mmproj; correct on a synthetic probe; untrained | no (501) | **yes, trained** | Clef-Flash where image accuracy matters |
| one question, warm (samples t1) | 0.24 to 0.42 s | 0.16 to 0.30 s | **0.17 to 0.21 s** | Clef-Flash |
| five questions on one state, warm p50 | 1.57 s, 1,479 tokens | 0.79 s, 1,721 tokens | **0.34 s, 868 tokens** | Clef-Flash |
| JevBench p95 (long states) | 2.40 s | 1.14 s | **0.86 s** | Clef-Flash |
| VRAM | 21.0 GB at 32k; 22.3 GB with mmproj | **13.1 GB at 8k** | 13.8 GB at 16k with mmproj | Winnow, Clef-Flash |
| cold load | 4.6 s | 3.3 s | 3.7 s | |
| license | Apache-2.0 | Apache-2.0 | Apache-2.0 | tie |

Published figure: the task named 0.909 on the public test (210/231) and hard ECE 0.089. No source for these numbers was found on 2026-10-08 (board JSON v1.6.0 and v1.6.1, model card revisions, quyet.ai, quyet repository, jevbench repository). The result is 208, two items under 210 and one outside the decision-002 tolerance. Prompt, tokens, temperatures and labels are verified equal, so the remaining explanation is Q4_K_M against the author's bf16; a larger quant does not fit the 3090 with room (Q5_K_M 21.9 GB, Q8_0 32.7 GB).

Calibration reading: Quyet's sharpness varies with the case like the teacher's (0.58 on `churn_risk`, 1.00 on `category`, 0.54 on the split `needs_human`), unlike Winnow's constant sharpness. On score questions it is sharper than the teacher, which is where its KL (0.270) loses to Clef-Flash (0.209). Both are usable distributions; Winnow's is not.

Throughput reading: one prompt per question on a 31B model. Clef-Flash answers all questions on one state in one prompt on a 9B model: 4.6 times faster on five questions and 3 times faster at p95 on long states.

## Decision

1. Route: metadata-only conversion with type `openjev`, as in decision-002 item 1 for `nimble`. The recipe in doc-007 held for the second model without changes to the copy script; only the template is model-specific. Images reach an `openjev` model through the server's mtmd path when the preset has an `mmproj`.
2. The decision-002 requirement-to-model table changes in three rows:

| requirement | decision-002 | now | reason |
|---|---|---|---|
| text only, accuracy on choice and score questions is the priority | Winnow-12B Q8_0 | **Quyet-1.0-Large Q4_K_M** | 208 against 198 on JevBench public, 0.804 against 0.702 on typed-decisions, better on every question type |
| image input | Clef-Flash Q8_0 | **Quyet-1.0-Large Q4_K_M with mmproj**, Clef-Flash when image accuracy must be known | the image path works and answered a probe like Clef-Flash; Quyet never trained on images and no image benchmark was run |
| calibrated probabilities | Clef-Flash Q8_0 | **Quyet-1.0-Large Q4_K_M** | Brier against the teacher equal (0.111 against 0.110), KL close (0.270 against 0.209), JevBench ECE better (0.043 against 0.058), and the accuracy gap is 10 points |
| throughput, several questions on one state | Clef-Flash Q8_0 | Clef-Flash Q8_0 | 0.34 s against 1.57 s for five questions |
| VRAM headroom (a chat model or a second service must stay resident, or the 3090 is shared) | not a row | Clef-Flash Q8_0 or Winnow-12B Q8_0 | Quyet leaves 2 GB on the 3090 |

   Winnow has no row. It stays installed as the Gemma 4 12B reference and for the 8k, 13 GB case where Quyet does not fit; doc-007 remains the recipe document.
3. Recommended saturn configuration for the 3090: preset `quyet-large-Q4` (doc-009): `Quyet-1.0-Large.Q4_K_M-systemone.gguf`, `mmproj = Quyet-1.0-Large.mmproj-f16.gguf`, `ctx-size = 32768`, `jinja = true`, with the `[*]` defaults (q8_0 KV, flash attention, `-ngl 99`, `parallel = 1`). Quant Q4_K_M; no fresh quant. 16k and q4_0 KV were not needed.
4. Tolerance rule (decision-002 item 4) stands. Quyet is adopted with a recorded 2-item gap to a figure whose source is unknown, because the prompt equality is proven and no author figure exists on the 231-item set. If the author publishes a 231-item figure, compare again.
5. Client-side caveats, documented in doc-009 and to be enforced by numpty when a model profile exists (NUMP-007 scope): at most 10 options per question (the server allows 52), prompts under 8,000 tokens (the server allows 32k), `confidence` is the TypeSafe formula and not Quyet's `p_max`, choice criteria must be an object.

## Consequences

- numpty docs name Quyet as the local decision model for text accuracy, images and calibrated probabilities, Clef-Flash for throughput and VRAM headroom, and show the preset. decision-002's table is superseded in the rows above; its route decision (item 1) and tolerance rule (item 4) stand.
- Loading Quyet unloads the resident model (`--models-max 1`); a chat model and Quyet cannot be co-resident on the 3090. Workloads that interleave chat and decisions pay a load (4.6 s) at each switch, or use Clef-Flash.
- Quyet's 31B prompts cost about 1.5 s per five-question case; a client sending many questions per state should batch per request (the server runs them sequentially anyway) and expect 0.3 s per question.
- doc-006's watch list drops Quyet. Its next run looks for a Quyet-1.0-Large imatrix or Q5 quant that fits, a published 231-item figure, and the Medium (4B) model as a small alternative to lev.
- The image row is provisional. An image benchmark (ImageJevBench, as for Clef-Flash on the board) would settle it; that is a new spike, not scheduled here.
- Follow-up candidates (not created): the numpty model-profile limits in item 5; an ImageJevBench run; the Quyet-1.0-Medium conversion (Qwen3.5-4B, same prompt code, type openjev) as a lev replacement.
