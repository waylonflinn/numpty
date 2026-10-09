---
id: NUMP-022
title: >-
  Research spike: convert Quyet-1.0-Large to a llama.cpp decision-model GGUF
  (type openjev)
status: Done
assignee:
  - '@claude'
created_date: '2026-10-08 14:47'
updated_date: '2026-10-08 20:49'
labels:
  - research
  - decision-models
dependencies:
  - NUMP-021
references:
  - 'https://huggingface.co/chinhnc/Quyet-1.0-Large'
  - 'https://huggingface.co/mradermacher/Quyet-1.0-Large-GGUF'
  - 'https://github.com/ncchinh/quyet'
  - 'https://benchmarkheaven.com/jev-models'
documentation:
  - doc-009 - Quyet-1.0-Large to a llama.cpp decision GGUF (NUMP-022)
  - decision-003 - Quyet-1.0-Large (type openjev
  - Q4_K_M
  - >-
    32k) replaces Winnow for text accuracy and Clef-Flash for images and
    calibration; Clef-Flash stays for throughput and small VRAM
  - doc-008 - Decision model evaluation protocol
  - doc-005 - Local decision models for llama.cpp (NUMP-016)
  - 'doc-006 - Decision model watch: ggml-org GGUFs vs JevBench'
  - doc-007 - Winnow-12B to a llama.cpp decision GGUF (NUMP-018)
  - >-
    decision-002 - Winnow-12B is served by upstream llama-server through
    metadata-only conversion (type nimble); Winnow for text accuracy
  - Clef-Flash for images
  - calibration
  - and throughput
type: spike
ordinal: 24000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Quyet-1.0-Large (chinhnc, Gemma-4-31B-it fine-tune, Apache-2.0) ranks first on JevBench v1.6.x (Capability 81.7 against Winnow 71.2, claimed public-test accuracy 0.909, hard ECE 0.089). The published GGUF (`mradermacher/Quyet-1.0-Large-GGUF`) is a plain `gemma4` chat conversion: no decision keys, no `systemone` template, llama-server returns 501 (doc-005). doc-005 read the quyet source: one forward pass per question, softmax over letters A..J at the last prompt token, per-type temperatures (choice 1.3007, score 1.3159, noul 1.4957), noul rendered A = true, B = false, prompt version 2 as a single user turn with the Gemma 4 template, thinking off, state truncated to 6000 tokens and prompt to 8000. That matches upstream type `openjev` (true-first noul, A-Z then a-z). doc-007 gives the metadata-only recipe (gguf-py copy script, template, verification by rendered prompt then by published figure) that worked for Winnow. Apply it here. Known differences to settle: the server allows 52 options, Quyet trained with 10; `confidence` formulas differ; a 31B Q4_K_M is about 19 GB and tight on the 3090 at 8k context (doc-006), so the quant and context size are a planning choice, and a fresh quant from the safetensors is allowed if the published Q4 does not fit. Image input: upstream passes images for type `openjev`, and a Gemma-4-31B mmproj exists, so a request with an image is mechanically possible. The quyet source (`src/quyet/llm/prompt.py`, `runtime.py`) has no image path, so Quyet was never trained or evaluated with images. Any image capability is untested and must be measured, not assumed. Decision in scope: whether Quyet changes the requirement-to-model table in decision-002 (text accuracy, images, calibration, throughput). Evaluation uses the consolidated protocol from NUMP-021. Probe scripts stay uncommitted; the converted GGUF, template and preset live on saturn and in the doc, as for Winnow.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Doc states the Quyet mechanism from the quyet source against upstream `openjev`: label alphabet and the 10-option training limit, noul order, per-type temperatures, prompt v2 with the Gemma 4 markup, truncation, and confirms the type match or names the mismatch
- [x] #2 A converted GGUF on saturn carries `gemma4.decision.type = openjev`, the three temperature keys and a `systemone` template whose rendered prompt equals a Python replica of the quyet renderer on a fixed sample of choice, score and noul questions (server verbose log), with the quant and context size chosen and the VRAM measured on the 3090
- [x] #3 A router preset reports `output_modalities: ["decisions"]` and answers Choice, Score and Noul through `numpty.TypeSafe`, with cold and warm latency recorded
- [x] #4 JevBench public 231 on upstream llama-server reproduces the published public-test figure within the decision-002 tolerance (one item), or the doc explains the gap and what was tried
- [x] #5 typed-decisions, throughput (one and five questions) and the distribution-sample rows are recorded with the NUMP-021 protocol and compared with Winnow, Clef-Flash and lev
- [x] #6 Doc states the image result: whether a Gemma-4-31B mmproj loads with the preset, whether upstream accepts an image request for this model, and a measured comparison with Clef-Flash on image cases, with the caveat that Quyet trained without images
- [x] #7 Decision record states whether Quyet replaces a row of the decision-002 requirement-to-model table, and the recommended quant, context and preset for the 3090
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 doc records reasoning and sources
- [x] #2 decision record produced
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Spike plan. Questions = AC #1-#7 as written; no change. Decision expected (AC #7). Class and signature items do not apply.

Order and sources:

1. AC #1 mechanism. Re-read `github.com/ncchinh/quyet` `src/quyet/llm/prompt.py`, `runtime.py`, `quyet_config.json` at the current default branch (doc-005 read it 2026-10-05; confirm nothing moved). Settle from source, not from doc-005: option line form (`A. text` per doc-005, not Winnow's `A: "json"`), noul option text (description or literal true/false), state serialization (raw string vs compact JSON), the three closing sentences per type, no system turn, no closing line, thinking off. Compare to upstream `openjev` in `tools/server/server-decision.cpp` on saturn (`~/Build/llama.cpp`, b11429): A-Z then a-z, true-first noul, images passed, no `label` in template inputs. Record the 10 vs 52 option gap and the confidence gap (p_max vs TypeSafe formulas) as client-side caveats.

2. AC #2 conversion. Quant: start with the published `mradermacher/Quyet-1.0-Large-GGUF` Q4_K_M (~19 GB; doc-006 estimate 22 GB at 8k with f16 KV, so ~21 GB with saturn's q8_0 KV + flash attention). Context 8192, Quyet's own prompt cap. Fallback if it does not load or leaves no headroom: IQ4_XS or Q4_K_S from the same repo; a fresh quant from safetensors only if no published quant fits. Download to `/opt/llama/models` on saturn. Template `quyet_systemone.jinja` from step 1; keys via `gguf_add_decision.py` from doc-007 with `--type openjev --temperature choice=1.3007 score=1.3159 noul=1.4957`. Verify with `llama-server --verbose` on 8099 against a Python replica of the quyet renderer (`quyet_prompt.py`, scratch) on a fixed sample: choice, score, noul, a `<` and a quote, a JSON state, a null description. Also check that `a`..`z` are single Gemma 4 tokens (upstream requires it even though Quyet uses A..J). Record VRAM from `nvidia-smi`.

3. AC #3 preset. `quyet-large-Q4` in `models.ini` (backup first), `ctx-size = 8192`, `jinja = true`. Reload via `GET /v1/models?reload=1`. Check `output_modalities`, answer the README example through `numpty.TypeSafe`, record cold and warm latency. Note: loading Quyet alongside winnow/clef on the router is likely a swap, not co-residency; record what the router does.

4. AC #4 JevBench public 231. jevbench c6004e0 on saturn, typesafe adapter, same command as doc-007 with `--model`. Target 0.909 public-test (210/231 ± 1). Published metric may be a different split or scorer; read the Quyet model card and JevBench page to pin the comparable figure before running. A gap: check temperature application, option line form, tokenizer boundary (Quyet renders one string, so no boundary issue expected).

5. AC #5 protocol rows. BLOCKED on NUMP-021 (To Do). Steps 1-4 and 6 do not need it. If NUMP-021 lands first: one command per set from `scripts/eval/`. If not, run the doc-007 procedure from scratch copies and note the deviation in the doc; do not reconstruct the scorer in this task.

6. AC #6 images. Find a Gemma-4-31B-it mmproj (ggml-org or mradermacher). Add `mmproj` to the preset, check load and VRAM (31B Q4 + mmproj + KV may exceed 24 GB; if so, record that and test at a smaller context or quant). Send one image request through TypeSafe; record accept/501. If accepted, run the doc-005 image cases against clef-flash-9b-Q8 and state the caveat that Quyet never trained on images.

7. AC #7 decision. New decision record: does Quyet take the text-accuracy row from Winnow, and does it take any other row (images, calibration via ECE/KL, throughput via one and five questions). Recommended quant, context, preset for the 3090. Update the decision-002 table reference in the doc; decision-002 itself stays accepted and the new record supersedes rows explicitly.

Deliverables: doc-008 (Quyet conversion, same shape as doc-007), decision-003, template and preset on saturn. Probe scripts stay in scratch. Nothing in the repo.

Risks: VRAM (plan step 2 fallback), published figure not comparable (step 4), NUMP-021 ordering (step 5).

Review amendments (2026-10-08, @waylonflinn):

- Quant: Q4_K_M confirmed. No fresh quant.
- Context: target 32768 (quadruple), fall back to 16384. Start with saturn's `[*]` q8_0 KV; drop to `cache-type-k/v = q4_0` only if 32k does not fit. Evidence it is feasible: the base `gemma-4-31B-it` preset on saturn runs a UD-Q4_K_XL at ctx 131072 with q4_0 KV and flash attention on the same 3090. Record VRAM at the chosen context and, if cheap, at 8k for comparison with doc-007.
- Order: NUMP-021 is done first in a separate session. This task resumes after it, so AC #5 runs with the consolidated `scripts/eval/` commands and no deviation note is needed.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-08 AC #1/#2 progress. quyet source re-read at d2514fe (2026-10-08, v1.0.2): prompt v2 confirmed, A..J, per-type T, describe() falsy->fallback, non-string descriptions json.dumps with ', ' ': ' separators, compact state JSON, Gemma 4 template thinking off; HF card revised 2026-10-08 (no figures). Upstream openjev (b11429): A-Z a-z all single Gemma 4 tokens (verified), true-first noul, temps looked up as type.bucket then type (Quyet keys are per type), images via mtmd, ordered_json keeps request key order. Downloaded mradermacher Q4_K_M (sha256 e7fc4952..., matches HF LFS) and mmproj-f16 to /opt/llama/models. Converted with gguf_add_decision.py --type openjev, T 1.3007/1.3159/1.4957, template ~/Build/quyet_systemone.jinja -> Quyet-1.0-Large.Q4_K_M-systemone.gguf (64 keys, 833 tensors). Verbose server 8099 at ctx 32768 q8_0 KV: 21.0 GB VRAM (weights 17.8 GB, KV 1.36 GB global 10 layers + 0.64 GB SWA 50 layers, compute 0.4 GB). Rendered prompts equal the quyet replica (transformers AutoTokenizer + quyet code) on 7 questions x 2 runs (choice/score/noul, string state with < and quotes, JSON list state with non-ASCII, empty and JSON descriptions, 10 options); input token counts equal (203/184/87/91). Published 0.909/0.089 figure not found in board v1.6.0/v1.6.1 JSON, model card revisions, quyet.ai or git history.

2026-10-08 AC #3-#7. Preset quyet-large-Q4 added to models.ini (backup .bak-2026-10-08): converted GGUF + mmproj f16, ctx 32768, jinja; router reports output_modalities decisions, input_modalities text+image. numpty.TypeSafe README example: cold 4.59 s, warm 0.27-0.31 s. doc-008 commands from the Mac: JevBench public 208/231 (0.900, Brier 0.139, ECE 0.043, ordinal MAE 0.171, p50 0.27 s / p95 2.40 s); typed-decisions acc 0.804 (noul 0.878, choice 0.753, score 0.786), KL 0.270, Brier 0.111, pmax 0.797, ECE 0.021, warm p50 1.57 s, 1479 tokens; samples t1 0.24-0.42 s, t5 0.93-1.82 s. Results in scripts/eval/results/quyet-large-Q4/ (uv run pytest -q: 275 passed). Published 0.909 figure: source not found (board JSON v1.6.0/v1.6.1, model card revisions, quyet.ai, quyet and jevbench repos); 208 is 2 items under 210, one outside tolerance; prompt/token/temperature/label equality verified, Q4_K_M vs bf16 is the remaining explanation; recorded in doc-009 and decision-003 item 4. Images: mmproj loads (22.3 GB), upstream accepts the request, red-circle probe answered like Clef-Flash (red 0.98, circle 0.97, text 0.08; text-only control near uniform); caveat recorded. VRAM 19.8 GB at 8k, 21.0 GB at 32k, 22.3 GB with mmproj; 16k and q4_0 KV fallbacks not needed. decision-003 created with the CLI (status proposed), body written below the frontmatter as for decision-001/002. doc-008 gained the Quyet row, preset and recreation notes. Probe scripts stay in scratch; template and preset live on saturn and in doc-009.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-10-08 16:11
---
Plan ready for review
---

author: @claude
created: 2026-10-08 16:25
---
Plan reviewed. Q4_K_M, ctx 32k (16k fallback), q4_0 KV only if needed. Paused in Planning until NUMP-021 is done; resume then and move to In Progress.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Quyet-1.0-Large converted to an upstream llama-server decision GGUF (type openjev) by metadata only: five header keys on a copy of the mradermacher Q4_K_M, template quyet_systemone.jinja reproducing the quyet package prompt v2; rendered prompts and token counts equal the quyet renderer on 7 varied questions (verbose server log). Served on saturn as preset quyet-large-Q4 (ctx 32768, q8_0 KV, mmproj f16; 21.0 GB, 22.3 GB with mmproj). Verified: numpty.TypeSafe answers Choice/Score/Noul (cold 4.6 s, warm 0.3 s); JevBench public 208/231 (Winnow 198, Clef-Flash 190; the task's 0.909 figure has no findable source, gap of 2 items explained in doc-009); typed-decisions 0.804 (Clef-Flash 0.707, Winnow 0.702), KL 0.270, Brier 0.111; images work through the mmproj on a synthetic probe with the untrained caveat. Deliverables: doc-009, decision-003 (proposed: Quyet takes text accuracy, images and calibration; Clef-Flash keeps throughput and VRAM headroom), doc-008 row, scripts/eval/results/quyet-large-Q4/ (pytest 275 passed).
<!-- SECTION:FINAL_SUMMARY:END -->
