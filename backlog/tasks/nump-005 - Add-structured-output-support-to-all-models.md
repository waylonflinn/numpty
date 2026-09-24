---
id: NUMP-005
title: Add structured output support to all models
status: To Do
assignee: []
created_date: '2026-09-24 17:13'
labels: []
dependencies: []
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Let a caller request a response that conforms to a JSON schema, and receive the parsed result. Support must work the same way across `AnthropicMessages`, `OpenAIChat`, and `OpenAIResponses`, using each provider native mechanism.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A caller can supply a schema and get a parsed, validated result from every provider model
- [ ] #2 The interface is provider-neutral
- [ ] #3 Invalid or refused output produces a clear error
- [ ] #4 Tests cover rendering and parsing for each provider offline
- [ ] #5 Public API is documented
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 tests pass
- [ ] #2 docstrings are up to date
<!-- DOD:END -->
