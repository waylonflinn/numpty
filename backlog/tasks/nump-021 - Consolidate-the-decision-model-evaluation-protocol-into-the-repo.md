---
id: NUMP-021
title: Consolidate the decision-model evaluation protocol into the repo
status: To Do
assignee: []
created_date: '2026-10-08 14:47'
labels:
  - decision-models
dependencies: []
references:
  - 'https://github.com/fstandhartinger/jevbench'
  - 'https://huggingface.co/datasets/LocalLLaMA/typed-decisions'
documentation:
  - doc-005 - Local decision models for llama.cpp (NUMP-016)
  - doc-007 - Winnow-12B to a llama.cpp decision GGUF (NUMP-018)
  - >-
    decision-002 - Winnow-12B is served by upstream llama-server through
    metadata-only conversion (type nimble); Winnow for text accuracy
  - Clef-Flash for images
  - calibration
  - and throughput
type: chore
ordinal: 23000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Three spikes (NUMP-016, NUMP-016.01, NUMP-018) evaluated local decision models on saturn with the same procedure: JevBench public 231 items through the jevbench CLI with the typesafe adapter, the typed-decisions all/test split (400 cases, 2,000 decisions) through a scorer that measures accuracy, KL and Brier against the teacher distribution, warm latency for one and five questions, and sample distributions. The method is described in doc-005 and doc-007 and the tolerance rule is decision-002 item 4, but the scorer (`td_probe.py`), the sample script (`td_examples.py`) and the dataset parquet live only in session scratch directories under /private/tmp, and the JevBench clone and results live on saturn under ~/Build. The spike rule kept them out of the repo. They have now been reused on three models and are infrastructure, not probes. The next model evaluation (Quyet-1.0-Large) should be one command per set, not a reconstruction. Scope: scripts in the repo, a Backlog doc that states the protocol, and a durable home for the per-model results. Out of scope: `scripts/jev_xref.py` (the doc-006 watch script, kept uncommitted on purpose) and any change to numpty library code.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Scripts under `scripts/eval/` run from the Mac against the saturn router with a model id argument: the typed-decisions scorer, the distribution-sample script, and a JevBench run-and-summarize wrapper (or documented invocation of the jevbench CLI on saturn)
- [ ] #2 The typed-decisions scorer reproduces the uniform baseline (KL 0.444, Brier 0.238) and the recorded clef-flash-9b-Q8, winnow-12b-Q8 and lev-4b-Q8 figures in doc-007 within rounding
- [ ] #3 A Backlog doc "Decision model evaluation protocol" states the fixed sets and revisions (jevbench c6004e0 public files, typed-decisions all/test), each metric and its target (one-hot label for JevBench, teacher distribution for typed-decisions, ECE), the saturn settings (router, one request at a time, Q8_0 weights, q8_0 KV), the throughput method, the distribution-sample rows, and the tolerance rule from decision-002
- [ ] #4 Per-model result summaries for the three models already measured are stored in a location the doc names, and a new model run adds one file without editing the scripts
- [ ] #5 The doc lists what still lives only on saturn (jevbench clone, raw results, start8099.sh, models.ini presets) and how to recreate it
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 tests pass
- [ ] #2 docstrings are up to date
<!-- DOD:END -->
