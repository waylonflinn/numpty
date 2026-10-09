---
id: NUMP-027
title: >-
  Promote chat_decide.py into scripts/eval: the structured-output decision route
  for chat models
status: To Do
assignee: []
created_date: '2026-10-09 16:41'
labels:
  - decision-models
  - eval
dependencies:
  - NUMP-026
references:
  - scripts/eval/harness.py
  - scripts/eval/td_score.py
  - scripts/eval/jevbench.py
documentation:
  - >-
    doc-011 - One Gemma 4 31B file for chat and decisions: stock Gemma with
    decision keys
  - Quyet for both roles
  - and structured output (NUMP-026)
  - doc-008 - Decision model evaluation protocol
  - >-
    decision-005 - Two files with the switch: Quyet stays the decision model and
    the chat preset the chat model; stock Gemma 4 31B with decision keys loses
    29 JevBench items
  - >-
    and chat plus structured output matches Quyets accuracy but not its
    calibration
type: chore
ordinal: 30000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
NUMP-026 (doc-011) measured decisions through POST /v1/chat/completions with a strict JSON schema and the jevbench openai_compat prompt, so that a chat model answers choice, score and noul questions without decision metadata. The scratch script chat_decide.py (saturn ~/Build/numpty-eval/probes/nump-026/, the NUMP-026 session scratchpad) reproduced that prompt and schema for typed-decisions and fed the doc-008 scorer unchanged; the JevBench side ran through the jevbench adapter directly (jev_chat.sh). The route is the only one for models that cannot be converted (cloud Sonnet, Luna) and is the labeling tool for a self-distillation decision LoRA, so it needs to be a committed command with the same three-command shape as doc-008: typed-decisions, samples, JevBench. decision-005 names it the fallback route when the chat file must stay resident. The thinking switch (enable_thinking true or false) and the sampling must be arguments, because the thinking-on row differs by 18 JevBench items and 4x latency. The route must stay separate from the systemone route in results/ because the probabilities are verbalized.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A `scripts/eval` command runs typed-decisions through chat completions with the doc-011 prompt and schema, a thinking on/off flag and a model id, and writes a result file with the doc-008 aggregates plus schema validity, output tokens per decision, p50 and p95 latency and a verbalized-probabilities marker
- [ ] #2 A `scripts/eval` command runs JevBench public through the jevbench openai_compat adapter with the same thinking flag, price 0, and stores the summary like `jevbench.py` does
- [ ] #3 The stored result for the thinking-off Gemma 4 31B route reproduces the doc-011 figures within the doc-008 tolerance (JevBench 209/231 within one item; typed-decisions accuracy 0.729, KL 0.851 and Brier 0.181 within 0.0015)
- [ ] #4 Results live under a directory name that marks the route (for example `results/<model>-chat/`), never under the systemone model directory, and `tests/test_eval.py` covers the stored chat-route file
- [ ] #5 doc-008 documents the commands, the prompt and schema source, the verbalized-probabilities caveat and the result layout
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 tests pass
- [ ] #2 docstrings are up to date
<!-- DOD:END -->
