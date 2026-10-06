---
id: NUMP-018
title: >-
  Research spike: convert a Jev-style model to a llama.cpp decision-model GGUF
  (Winnow-12B first)
status: To Do
assignee: []
created_date: '2026-10-06 21:43'
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
type: spike
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Upstream llama-server (v0.6.0, build b11361 and later) serves `POST /v1/systemone` only for a GGUF that declares itself a decision model: key `{arch}.decision.type` (openjev, lev, kev, nimble, laya, clef), temperature keys `{arch}.decision.temperature.{choice|score|noul}`, and a named chat template `tokenizer.chat_template.systemone`. Without them the server returns 501 (doc-005). The strongest Jev-style models on JevBench do not ship that metadata. Winnow-12B (EldanRing, Gemma-4-12B-it LoRA merged, Apache-2.0, JevBench rank 6, Capability 71.2) ships Q8_0 (12.7 GB) and NVFP4 (8.2 GB) GGUFs whose header has no decision keys. It runs only on the author's llama.cpp fork (winnow-inference, a pinned revision plus a typed-decision patch). It is about 10 Capability points above lev and Clef-Flash, the models numpty recommends today (decision-001), and it fits the RTX 3090 on saturn. doc-005 sketched the same gap for Quyet-1.0-Large: its mechanism matches openjev, and the stock gguf-py scripts cannot add new keys, so a copy script or a converter change is needed. That sketch is unverified. The goal is a conversion procedure that works for Winnow now and for the next Jev-style model later (Quyet, decider-4b, torchcast, Cygnet). Decision expected. Converted GGUFs live on saturn (`/opt/llama/models`), not in the repo. Saturn takes one request at a time.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Doc states the decision mechanism Winnow uses, from the fork patch source: which upstream decision type it matches (or that none does), its label scheme, option limit, prompt with Gemma 4 markup, and per-type temperatures
- [ ] #2 Doc gives the exact metadata keys and `systemone` template a Winnow GGUF needs, and a tested way to write them into the published GGUF (gguf-py copy script or converter change) without re-quantizing
- [ ] #3 A converted Winnow GGUF on saturn reports `output_modalities: ["decisions"]` in upstream llama-server and answers Choice, Score, and Noul through `numpty.TypeSafe`
- [ ] #4 Doc compares answers of the converted GGUF on upstream llama-server with the author's fork or published figures on a fixed sample (for example a typed-decisions subset), and states whether the difference is within an agreed tolerance and why
- [ ] #5 Doc gives a general conversion recipe for other Jev-style models: what to read from a source model (mechanism, prompt, temperatures, labels), the steps, and when a model cannot be converted without an upstream decision type
- [ ] #6 Decision record states the chosen route (for example metadata-only conversion, upstream PR for a new decision type, or the author's fork) and whether to recommend Winnow over Clef-Flash in numpty docs
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 doc records reasoning and sources
- [ ] #2 decision record produced
<!-- DOD:END -->
