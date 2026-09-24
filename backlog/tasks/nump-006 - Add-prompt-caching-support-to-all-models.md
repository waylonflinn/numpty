---
id: NUMP-006
title: Add prompt caching support to all models
status: To Do
assignee: []
created_date: '2026-09-24 17:13'
labels: []
dependencies: []
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add prompt caching so repeated conversation prefixes (system prompt, tool definitions, earlier turns) are not billed and processed in full on each agent turn. Providers differ: Anthropic needs explicit cache breakpoints, OpenAI caches automatically but reports cache usage. The agent loop resends the full history every turn, so caching has a direct effect on cost and latency.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every provider model uses caching for the stable prefix of a conversation
- [ ] #2 Cache usage from each response is available to the caller
- [ ] #3 Caching can be turned off
- [ ] #4 Tests cover rendered cache markers offline
- [ ] #5 Public API is documented
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 tests pass
- [ ] #2 docstrings are up to date
<!-- DOD:END -->
