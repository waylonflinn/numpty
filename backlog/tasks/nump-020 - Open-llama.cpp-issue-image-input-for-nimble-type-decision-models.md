---
id: NUMP-020
title: 'Open llama.cpp issue: image input for nimble-type decision models'
status: To Do
assignee: []
created_date: '2026-10-07 20:21'
updated_date: '2026-10-08 14:25'
labels:
  - research
  - decision-models
dependencies: []
references:
  - 'https://github.com/ggml-org/llama.cpp'
  - 'https://github.com/ggml-org/llama.cpp/pull/29818'
  - 'https://huggingface.co/EldanRing/Winnow-12B'
documentation:
  - doc-007 - Winnow-12B to a llama.cpp decision GGUF (NUMP-018)
  - >-
    decision-002 - Winnow-12B is served by upstream llama-server through
    metadata-only conversion (type nimble); Winnow for text accuracy
  - Clef-Flash for images
  - calibration
  - and throughput
type: chore
ordinal: 22000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Winnow-12B (EldanRing, Gemma-4-12B-it LoRA, Apache-2.0) is a vision-capable decision model: the author's server takes images for typed decisions and ships `mmproj-Winnow-12B.gguf`. doc-007 converts the published GGUF to an upstream llama-server decision model by metadata only, with decision type `nimble` (labels A..Z then AA..ZZ, noul false first). Upstream gates image input by decision type, not by model: `server_decision_context::can_use_images()` in `tools/server/server-decision.h` returns true only for `openjev` and `clef`, and a request with images on any other type gets 501 before the projector is consulted. The only letter-logit type with images, `openjev`, swaps noul to true-first and uses `a`-`z` above 26 options, so it does not reproduce Winnow's training prompt. The template already renders the author's image block (`Images (in order):` plus one media marker per image before the state) and the mmproj is on saturn at `/opt/llama/models/mmproj-Winnow-12B.gguf`, so the server check is the only blocker. Ask upstream to allow image input for `nimble` (and `lev`) when an mmproj is loaded, or to make it a model key (for example `{arch}.decision.images = true`), and optionally a `{arch}.decision.noul_true_first` key so a template can match any training order. The issue should describe the change a later PR from us would make, with Winnow as the concrete case and the doc-007 figures as evidence that metadata-only conversion works. Posting is outward-facing: the user reviews and approves the draft before it is posted. decision-002 recorded "no upstream PR now"; an issue is in scope, a PR is not unless the user asks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A draft issue describes the problem (image gate by type), the Winnow case, and the proposed change (image input for nimble/lev with an mmproj, or a model key), with the doc-007 evidence
- [ ] #2 The user approves the draft before it is posted
- [ ] #3 The issue URL and posting date are recorded in this task and in doc-007
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 issue is posted on ggml-org/llama.cpp
<!-- DOD:END -->
