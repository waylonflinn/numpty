---
id: NUMP-022
title: >-
  Research spike: convert Quyet-1.0-Large to a llama.cpp decision-model GGUF
  (type openjev)
status: To Do
assignee: []
created_date: '2026-10-08 14:47'
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
- [ ] #1 Doc states the Quyet mechanism from the quyet source against upstream `openjev`: label alphabet and the 10-option training limit, noul order, per-type temperatures, prompt v2 with the Gemma 4 markup, truncation, and confirms the type match or names the mismatch
- [ ] #2 A converted GGUF on saturn carries `gemma4.decision.type = openjev`, the three temperature keys and a `systemone` template whose rendered prompt equals a Python replica of the quyet renderer on a fixed sample of choice, score and noul questions (server verbose log), with the quant and context size chosen and the VRAM measured on the 3090
- [ ] #3 A router preset reports `output_modalities: ["decisions"]` and answers Choice, Score and Noul through `numpty.TypeSafe`, with cold and warm latency recorded
- [ ] #4 JevBench public 231 on upstream llama-server reproduces the published public-test figure within the decision-002 tolerance (one item), or the doc explains the gap and what was tried
- [ ] #5 typed-decisions, throughput (one and five questions) and the distribution-sample rows are recorded with the NUMP-021 protocol and compared with Winnow, Clef-Flash and lev
- [ ] #6 Doc states the image result: whether a Gemma-4-31B mmproj loads with the preset, whether upstream accepts an image request for this model, and a measured comparison with Clef-Flash on image cases, with the caveat that Quyet trained without images
- [ ] #7 Decision record states whether Quyet replaces a row of the decision-002 requirement-to-model table, and the recommended quant, context and preset for the 3090
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 doc records reasoning and sources
- [ ] #2 decision record produced
<!-- DOD:END -->
