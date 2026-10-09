---
id: NUMP-029
title: >-
  Measure typed-decisions on Gemma 4 31B through chat plus structured output
  with thinking on
status: To Do
assignee: []
created_date: '2026-10-09 16:41'
labels:
  - decision-models
  - eval
dependencies:
  - NUMP-027
documentation:
  - >-
    doc-011 - One Gemma 4 31B file for chat and decisions: stock Gemma with
    decision keys
  - Quyet for both roles
  - and structured output (NUMP-026)
  - >-
    decision-005 - Two files with the switch: Quyet stays the decision model and
    the chat preset the chat model; stock Gemma 4 31B with decision keys loses
    29 JevBench items
  - >-
    and chat plus structured output matches Quyets accuracy but not its
    calibration
  - doc-008 - Decision model evaluation protocol
type: task
ordinal: 32000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
decision-005 keeps two files (Quyet for decisions, the chat preset for chat) because no one-file route met the margins on both evaluation sets. Its named reopen condition is the one measurement NUMP-026 did not run: typed-decisions (2,000 decisions) on the unmodified gemma-4-31b-Q4 chat preset through the structured-output route with thinking on. On JevBench public that route answered 227 of 231, every item that finished, against Quyet 208, but at 3.9 s median and 25 s p95 per question, and 4 items ran out of the 4,096-token budget while thinking (doc-011). The run takes about 3 h on saturn at 4 to 7 s per question, sequential, with the router otherwise idle, which is why it was left out of the spike. The result decides whether the resident chat file can serve decisions for workloads that accept several seconds per question, and it is the 31B ceiling that the decision LoRA spike (NUMP-028) trains toward. Run it with the committed command from NUMP-027 so the result is reproducible; record the token-limit failure count and whether a larger max_tokens changes it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 typed-decisions result for gemma-4-31b-Q4, chat plus schema, thinking on, stored by the NUMP-027 command: accuracy, KL, Brier, mean pmax, ECE by type and per question, schema validity, output tokens per decision, p50 and p95 latency, and the count of decisions that hit the token limit
- [ ] #2 The same figures beside the doc-011 rows (Quyet 0.804 / 0.270 / 0.111, thinking-off chat route 0.729 / 0.851 / 0.181) in doc-011 or a short new doc, with the verbalized-probabilities caveat
- [ ] #3 decision-005 is updated or superseded: either the reopen condition is met (thinking-on route at or above 0.804) and the resident-file rule changes, or it is not and the record says so with the measured gap
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 tests pass
- [ ] #2 docstrings are up to date
<!-- DOD:END -->
