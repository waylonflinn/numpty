---
id: NUMP-023
title: Publish the converted Winnow-12B decision GGUF to Hugging Face
status: To Do
assignee: []
created_date: '2026-10-08 14:54'
labels:
  - decision-models
dependencies: []
references:
  - 'https://huggingface.co/EldanRing/Winnow-12B'
  - 'https://github.com/ggml-org/llama.cpp/pull/29818'
documentation:
  - doc-007 - Winnow-12B to a llama.cpp decision GGUF (NUMP-018)
  - >-
    decision-002 - Winnow-12B is served by upstream llama-server through
    metadata-only conversion (type nimble); Winnow for text accuracy
  - Clef-Flash for images
  - calibration
  - and throughput
type: chore
ordinal: 25000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
NUMP-018 converted the published `EldanRing/Winnow-12B` Q8_0 GGUF into an upstream llama-server decision model by adding five header keys (`gemma4.decision.type = nimble`, three temperature keys, a `systemone` template); tensors are unchanged. doc-007 records the keys, template, copy script and the JevBench public reproduction (198/231 on b11429). The file works as-is on llama.cpp b11361 and later with no flags: the decision path renders the template with the server's own jinja runtime (`tools/server/server-decision.cpp`), not gated on `--jinja`. Older servers load it as a plain Gemma 4 chat model and return 501 on `/v1/systemone`. License: Apache 2.0; the author's NOTICE states the upstream Gemma 4 license is Apache 2.0 too, so redistribution with attribution is allowed. Today the file lives only on saturn (`/opt/llama/models/Winnow-12B-Q8_0-systemone.gguf`). Publishing lets other llama-server users run Winnow without the author's fork. The card must state the known limits from doc-007: text only (type nimble returns 501 on images, NUMP-020), one tokenizer-boundary difference from the fork, `confidence` by the TypeSafe formulas, the 64-option training limit not enforced by the server, Q8_0 only, verified on b11429 at 8k context. Subtask NUMP-023.01 asks the author to add the same keys at source; this repo is the interim. Posting is outward-facing: the user reviews and approves the card and the repo name before anything is uploaded.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A draft model card states provenance (source repo, revision, SHA256 of the input and output files), the exact modification (five keys, tensors unchanged), the minimum llama.cpp build, a run example with `llama-server` and a `/v1/systemone` request, the JevBench figure with build and date, and every limit listed in the description
- [ ] #2 LICENSE and NOTICE from the source repo are included, with a NOTICE line that records this modification
- [ ] #3 The published file's SHA256 equals the saturn file, and a fresh `llama-server` on the Mac or saturn loads it from the Hugging Face URL and reports `output_modalities: ["decisions"]`
- [ ] #4 The user approves the card and repo name before upload
- [ ] #5 doc-007 and decision-002 record the repo URL and the publish date
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 tests pass
- [ ] #2 docstrings are up to date
<!-- DOD:END -->
