---
id: NUMP-004
title: Support a local Qwen model
status: To Do
assignee: []
created_date: '2026-09-24 17:13'
updated_date: '2026-09-24 21:43'
labels: []
dependencies: []
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Test, develop, and document compatibility with a Qwen model served locally (for example through an OpenAI-compatible server). `OpenAIChat` already accepts `base_url` and `api_key` for this purpose, but this path has not been tested against a real local model. Tool calling, reasoning output, and message rendering may differ from the hosted OpenAI API.

Considerations:
- `OpenAIChat` does not read or send `Reasoning`. Newer OpenAI models do not expose reasoning through the Chat Completions API, so it was left out. Local reasoning models (Qwen) may return reasoning in this API (for example a `reasoning_content` field or `<think>` tags in the text). Decide whether to parse it and send it back between turns.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 An agent with tools completes a multi-turn tool-calling conversation against a local Qwen model
- [ ] #2 Differences from the hosted APIs are fixed or documented
- [ ] #3 README documents how to connect to a local Qwen model
- [ ] #4 Tests cover any Qwen-specific rendering or parsing, and run offline
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 tests pass
- [ ] #2 docstrings are up to date
<!-- DOD:END -->
