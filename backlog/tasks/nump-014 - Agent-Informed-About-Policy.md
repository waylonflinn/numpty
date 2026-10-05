---
id: NUMP-014
title: Agent Informed About Policy
status: To Do
assignee: []
created_date: '2026-09-29 21:22'
updated_date: '2026-09-30 23:24'
labels: []
dependencies:
  - NUMP-008
references:
  - src/numpty/agent.py
  - src/numpty/policy.py
ordinal: 14000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A model does not know the policy until a tool call is denied (NUMP-008). Each denial wastes a turn, and a low-reliability local model can retry the same denied action. The model should know the restrictions before it calls a tool.

Agreed design (session 2026-09-29): `Policy` owns the text that describes it to a model. `Agent` owns where the text goes: it appends the text to the system prompt. Rejected: tool descriptions (`Agent` would edit tool text, a cross-layer change, repeated on every tool); a query tool (spends a call to save a call); denial messages only (still one wasted call).

Facts: `AnthropicMessages` and `OpenAIResponses` send only the first `SystemMessage` and ignore the others, so a second system message does not reach the model. Location scopes are checked against the current directory at each check. A model needs the absolute path. Text fixed at construction goes stale if the process changes directory.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `Policy` returns a plain-text description of its restrictions for a model, with absolute paths for location scopes
- [ ] #2 `Policy.UNRESTRICTED` has no description text
- [ ] #3 `Agent` with a restrictive policy adds the description to the system prompt text, and makes a system prompt if none was given
- [ ] #4 The description reaches the model with `AnthropicMessages`, `OpenAIChat`, and `OpenAIResponses`
- [ ] #5 The text states the policy as facts. It does not add other behavior instructions
- [ ] #6 Docstrings state that the text is fixed at construction
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 tests pass
- [ ] #2 docstrings are up to date
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Planning NUMP-009 (2026-09-30): Policy gets a Process.C_EXTENSIONS flag (replaces monitor_calls). fastaudit allows a short safe list of C extensions (numpy, pandas, PIL, matplotlib, orjson, pydantic-core) even without the flag. Wanted here: a Policy property that exposes that list, and the description text tells the model which extensions it can use.
<!-- SECTION:NOTES:END -->
