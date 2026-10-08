---
id: NUMP-023.01
title: >-
  Open EldanRing/Winnow-12B issue: add llama.cpp decision metadata to the
  published GGUFs
status: To Do
assignee: []
created_date: '2026-10-08 14:54'
labels:
  - decision-models
dependencies: []
references:
  - 'https://huggingface.co/EldanRing/Winnow-12B'
  - 'https://github.com/EldanRing/winnow-inference'
documentation:
  - doc-007 - Winnow-12B to a llama.cpp decision GGUF (NUMP-018)
parent_task_id: NUMP-023
type: chore
ordinal: 26000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The author ships Q8_0, BF16 and NVFP4 GGUFs plus an mmproj, all without llama.cpp decision metadata, so upstream llama-server serves them only as chat models and users need the author's fork (a pinned llama.cpp with eight patches and its own endpoint). doc-007 shows that five header keys (`gemma4.decision.type = nimble`, three temperature keys at 1.0, a `systemone` template that reproduces `native/protocol.h`) make the Q8_0 file a native upstream decision model, with the author's own JevBench public figure (198/231) reproduced on b11429. One run of the gguf-py copy script on their side fixes all three quants at source, and the ggml-org decision-models collection could then list the model. The issue carries the keys, the template, the script, the verification method (rendered prompt equal to the fork's on six questions, JevBench public within one item) and the two known differences (one tokenizer boundary, `confidence` formula). It also notes that type nimble has no image input upstream (NUMP-020). The parent task's Hugging Face repo is the interim and the issue should link it when it exists. Posting is outward-facing: the user reviews and approves the draft before it is posted.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A draft issue describes the problem (fork required), the proposed change (five keys plus template, applied to all published GGUFs), the script and template verbatim, and the verification evidence from doc-007
- [ ] #2 The user approves the draft before it is posted
- [ ] #3 The issue URL and posting date are recorded in this task and in doc-007
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 tests pass
- [ ] #2 docstrings are up to date
<!-- DOD:END -->
