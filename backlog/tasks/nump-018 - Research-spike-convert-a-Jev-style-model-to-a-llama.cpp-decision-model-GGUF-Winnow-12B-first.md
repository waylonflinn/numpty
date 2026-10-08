---
id: NUMP-018
title: >-
  Research spike: convert a Jev-style model to a llama.cpp decision-model GGUF
  (Winnow-12B first)
status: Done
assignee:
  - '@claude'
created_date: '2026-10-06 21:43'
updated_date: '2026-10-08 14:25'
labels:
  - research
dependencies: []
references:
  - 'https://huggingface.co/EldanRing/Winnow-12B'
  - 'https://github.com/EldanRing/winnow-inference'
  - 'https://benchmarkheaven.com/jev-models/winnow-12b'
documentation:
  - doc-005 - Local decision models for llama.cpp (NUMP-016)
  - 'doc-006 - Decision model watch: ggml-org GGUFs vs JevBench'
  - >-
    decision-001 - NUMP-007 targets the System One wire protocol; Clef-Flash and
    lev first
  - doc-007 - Winnow-12B to a llama.cpp decision GGUF (NUMP-018)
  - >-
    decision-002 - Winnow-12B is served by upstream llama-server through
    metadata-only conversion (type nimble); Winnow for text accuracy
  - Clef-Flash for images
  - calibration
  - and throughput
type: spike
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Upstream llama-server (v0.6.0, build b11361 and later) serves `POST /v1/systemone` only for a GGUF that declares itself a decision model: key `{arch}.decision.type` (openjev, lev, kev, nimble, laya, clef), temperature keys `{arch}.decision.temperature.{choice|score|noul}`, and a named chat template `tokenizer.chat_template.systemone`. Without them the server returns 501 (doc-005). The strongest Jev-style models on JevBench do not ship that metadata. Winnow-12B (EldanRing, Gemma-4-12B-it LoRA merged, Apache-2.0, JevBench rank 6, Capability 71.2) ships Q8_0 (12.7 GB) and NVFP4 (8.2 GB) GGUFs whose header has no decision keys. It runs only on the author's llama.cpp fork (winnow-inference, a pinned revision plus a typed-decision patch). It is about 10 Capability points above lev and Clef-Flash, the models numpty recommends today (decision-001), and it fits the RTX 3090 on saturn. doc-005 sketched the same gap for Quyet-1.0-Large: its mechanism matches openjev, and the stock gguf-py scripts cannot add new keys, so a copy script or a converter change is needed. That sketch is unverified. The goal is a conversion procedure that works for Winnow now and for the next Jev-style model later (Quyet, decider-4b, torchcast, Cygnet). Decision expected. Converted GGUFs live on saturn (`/opt/llama/models`), not in the repo. Saturn takes one request at a time.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Doc states the decision mechanism Winnow uses, from the fork patch source: which upstream decision type it matches (or that none does), its label scheme, option limit, prompt with Gemma 4 markup, and per-type temperatures
- [x] #2 Doc gives the exact metadata keys and `systemone` template a Winnow GGUF needs, and a tested way to write them into the published GGUF (gguf-py copy script or converter change) without re-quantizing
- [x] #3 A converted Winnow GGUF on saturn reports `output_modalities: ["decisions"]` in upstream llama-server and answers Choice, Score, and Noul through `numpty.TypeSafe`
- [x] #4 Doc compares answers of the converted GGUF on upstream llama-server with the author's fork or published figures on a fixed sample (for example a typed-decisions subset), and states whether the difference is within an agreed tolerance and why
- [x] #5 Doc gives a general conversion recipe for other Jev-style models: what to read from a source model (mechanism, prompt, temperatures, labels), the steps, and when a model cannot be converted without an upstream decision type
- [x] #6 Decision record states the chosen route (for example metadata-only conversion, upstream PR for a new decision type, or the author's fork) and whether to recommend Winnow over Clef-Flash in numpty docs
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 doc records reasoning and sources
- [x] #2 decision record produced
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Research so far (2026-10-07, sources read, nothing changed)

Fork (`EldanRing/winnow-inference`, `runtime.lock.json`, `native/protocol.h`, `native/engine.h`, `patches/*`): pins upstream llama.cpp 911f6cdc (2026-09-18), two weeks before PR #29818 merged `/v1/systemone`; the fork has its own endpoint, not upstream's. Mechanism: one forward pass per question, logits of single-token labels at the last prompt token, softmax divided by one temperature (default 1.0, per request, not per type, no buckets). Labels A..Z then AA..ZZ, single-token only, at most 64 (`engine.h`). `llama-classifier-head.patch` is an optimisation: it projects only the label rows of the output tensor and applies Gemma's final logit softcap, equal to full-vocab logits at those rows (fork keeps a full-head parity mode). noul options are [false, true], answer is p(true). score = sum(i * p_i). Confidence = 1 - H/log K (differs from TypeSafe formulas). Prompt (`protocol.h`): `<|turn>system\n{fixed classification instruction}<turn|>\n<|turn>user\n[Images]State:\n{json}\n` then per question `\nQuestion: {json}\nOptions:\n{label}: {json}\n...Return the correct letter label.<turn|>\n<|turn>model\n<|channel>thought\n<channel|>Answer:\n`. Every value is nlohmann `dump()` (strings quoted, `<` written as the JSON escape for less-than (backslash u003c)); BOS added by tokenizer. Published GGUF header (checked on saturn): plain `gemma4`, 44 keys, no decision keys, file_type 7.

Upstream b11429 on saturn (`tools/server/server-decision.{h,cpp}`, `gguf-py/gguf/constants.py`): type `nimble` matches Winnow: labels A..Z, AA..ZZ single-token (up to 255), noul [false, true], option `label` text given to the template, temperature keys optional (default 1.0), text only (images 501). `openjev` does not: labels A-Z a-z and noul true-first (the server swaps, the template cannot undo it). Template inputs: id, type, instructions, state, options[{key, description, label}], questions, images; jinja has `tojson`. Keys: `gemma4.decision.type`, `gemma4.decision.temperature.{choice|score|noul}`, named template `systemone`.

Writing keys: `gguf_new_metadata.py` only exposes fixed flags, but its `copy_with_new_metadata(reader, writer, new_metadata, remove)` takes any key; a ~30-line script on saturn (`~/Build/llama.cpp/gguf-py`, numpy 1.26 present) copies tensors untouched. No re-quantization.

## Plan

1. Doc `doc-007 - Winnow-12B to a llama.cpp decision GGUF (NUMP-018)`: mechanism from the fork source (AC #1), sources, dates.
2. Write the `systemone` jinja template that reproduces the fork prompt from the upstream inputs (tojson for values, literal `<bos>`, thought channel, `Answer:\n`), and the gguf-py copy script. Both go into the doc verbatim; probe scripts stay uncommitted (spike rule).
3. Convert on saturn: `/opt/llama/models/Winnow-12B-Q8_0-systemone.gguf` (type nimble, three temperature keys 1.0, template). Add preset `winnow-12b-Q8` to models.ini (ctx 8192 first; tune later), `GET /v1/models?reload=1`, check `output_modalities: ["decisions"]`, answer the README example and `examples/decisions.json` through `numpty.TypeSafe` (AC #2, #3).
4. Parity (AC #4): build the fork on saturn (CUDA, pinned revision + 8 patches, ~15 GB under `~/Build`, run on 127.0.0.1:8091 only while the upstream server is idle, one request at a time). Compare on `tests/parity-requests.json`: prompt token ids (fork `/v1/winnow/inspect` with include_token_ids vs upstream tokenize of the rendered template) and per-option probabilities (fork `diagnostics: true`). Then JevBench public 231 (`fstandhartinger/jevbench` c6004e0, typesafe adapter, published 198/231) on upstream. Proposed tolerance: token-identical prompts; same argmax on every parity question; max |dp| <= 0.01 (same weights, same GPU, only matmul path differs); JevBench 198 +/- 1. Compare probabilities, not confidence (formulas differ by design).
5. Recipe (AC #5): what to read from a source model (label alphabet, noul order, option limit, prompt, temperatures, softcap/head), choose the upstream type by that table, write keys, verify by token parity then answer parity. Convertibility of Quyet (openjev, from doc-005), decider-4b, torchcast, Cygnet from their cards/source; list what has no upstream type (for Winnow: image input, >64 options cap).
6. Decision record (AC #6): route (metadata-only nimble conversion vs fork vs upstream PR for images) and Winnow vs Clef-Flash in numpty docs, using the JevBench run plus measured warm latency and VRAM on the 3090.
7. Update memory (saturn models) and doc-006 watch pointer; models.ini comment block for the new preset.

## Review questions

- AC #4 tolerance as proposed in step 4?
- Build the fork on saturn for the parity run (CUDA build, disk, time) or settle for the published 198/231 figure only?
- Decision scope: route + Winnow-vs-Clef-Flash only. Raising an upstream issue/PR for nimble image input is out of scope unless you want it in.
- New doc-007 rather than extending doc-005?

## Review outcome (2026-10-07)

Approved with changes: (a) no fork build; AC #4 compares the upstream server against the published JevBench public figure 198/231 (tolerance 198 +/- 1, same argmax semantics as the jevbench scorer); building the fork is a troubleshooting tactic if the figure is missed; (b) route is metadata-only (type nimble), no upstream PR now; (c) new doc-007.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-07 progress. Fork source read (protocol.h, engine.h, patches, runtime.lock.json): letter-logit mechanism, labels A..Z AA..ZZ (max 64), noul [false, true], one temperature 1.0, prompt with a system turn and `Answer:\n` after an empty thought channel; fork pins upstream 911f6cdc (pre-systemone). Upstream type nimble matches; openjev does not (noul true-first, labels a-z). Converted on saturn with a gguf-py copy script (reader to writer, 4 new keys, tensors untouched, 3.5 s from page cache): `/opt/llama/models/Winnow-12B-Q8_0-systemone.gguf`. Template verified byte-identical to a Python replica of the fork prompt on 6 test questions (server verbose log prints the rendered prompt); one fix needed: llama.cpp's jinja strips one trailing newline, so the template ends with two. Known inherent difference: the fork tokenizes prefix and suffix separately (`\n`,`\n` = 107,107), upstream tokenizes once (`\n\n` = 108). JevBench public 231 on upstream llama-server b11429: 198/231 = author's published figure, ECE 0.067, p50 0.08 s. Router preset `winnow-12b-Q8` added (models.ini backup .bak-2026-10-07); numpty.TypeSafe from the Mac answers Choice/Noul/Score, cold 3.3 s, warm 0.32 s, 13.1 GB VRAM at 8k. Subagent research on decider-4b, torchcast, Cygnet saved to scratch for the recipe section. Typed-decisions (400 cases) run in progress for the Clef-Flash comparison.

Finalization 2026-10-07. Evidence per AC: #1 doc-007 section "Winnow's decision mechanism" from protocol.h/engine.h/patches (type match: nimble). #2 doc-007 "Conversion": 5 keys, template, gguf_add_decision.py; run on saturn, header verified with GGUFReader (49 keys, 667 tensors), rendered prompt equal to the fork replica on 6 questions (server verbose log). #3 router `/v1/models` reports architecture.output_modalities ["decisions"] for winnow-12b-Q8; numpty.TypeSafe from the Mac answered Choice/Noul/Score (billing 0.9998, angry True 0.948, urgency 2.62), cold 3.3 s, warm 0.32 s. #4 JevBench public 231 via jevbench c6004e0: 198/231 = author's figure, Brier 0.2052 vs 0.2057, ECE 0.067 vs 0.074 (tolerance 198 +/- 1 met); same items Clef-Flash 190, lev 170; typed-decisions 0.702 vs author 70.0%, Clef-Flash 0.707. #5 doc-007 "Recipe" with the convertibility table (Quyet openjev; torchcast, Cygnet nimble; decider-4b partial). #6 decision-002 (proposed). Decision body written below the CLI frontmatter (no CLI path for decision content). doc-006 got a dated update paragraph. Memory updated. Nothing in the repo changed besides Backlog docs/decisions; scripts live in scratch and on saturn (~/Build). Open point for the reviewer: the decision title says "replaces Clef-Flash"; the body limits it to text, Clef-Flash stays for images and calibrated distributions.

2026-10-08 review: decision-002 reframed as situational (user). Body now has a Winnow/Clef-Flash tradeoff table and a requirement-to-model table: Winnow for text-only accuracy; Clef-Flash when images, calibration, or throughput (above all several questions per state) are required. doc-007 Decision paragraph updated to match. decision-002 title still says 'replaces Clef-Flash'; frontmatter is CLI-owned, so the title stays unless renamed by hand.

2026-10-08: decision-002 gained Throughput and Calibration subsections under the comparison table. Re-queried the first typed-decisions test case of each workflow on both models (scratch td_examples.py, uncommitted): one question warm 0.22 s Winnow vs 0.20 s Clef-Flash (9% saved), five questions 0.79 vs 0.36 s (54% saved, 2.2x), tokens 1,664 vs 856. Six example distributions (teacher, Clef-Flash, Winnow) show Winnow's constant sharpness against the teacher's varying spread.

2026-10-08: decision-002 title and file renamed by hand (user approval) to 'Winnow for text accuracy, Clef-Flash for images, calibration, and throughput'. NUMP-018 and NUMP-020 documentation entries updated through the CLI.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-10-07 17:05
---
Plan ready for review
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Winnow-12B now serves on upstream llama-server b11429 through a metadata-only GGUF conversion (type nimble, systemone template, temperature keys), preset winnow-12b-Q8 on saturn. Verified: rendered prompt equal to the fork's, JevBench public 198/231 (the author's figure; Clef-Flash 190, lev 170), typed-decisions 0.702 (author 70.0%), numpty.TypeSafe answers all three question types. doc-007 holds the mechanism, keys, template, script, comparison and the recipe for other Jev-style models; decision-002 (proposed) picks metadata-only conversion and Winnow over Clef-Flash for text.
<!-- SECTION:FINAL_SUMMARY:END -->
