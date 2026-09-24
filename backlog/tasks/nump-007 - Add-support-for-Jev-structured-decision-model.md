---
id: NUMP-007
title: Add support for Jev structured decision model
status: To Do
assignee: []
created_date: '2026-09-24 17:34'
labels: []
dependencies: []
references:
  - 'https://docs.typesafe.ai/introduction/quickstart'
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Jev (TypeSafe, `typesafe-sdk`) is a structured decision model: likely an LLM tuned and served for zero-shot classification and regression. Its creators call it a "System One" model. It does not fit the chat-style `Model` interface: `TypeSafeClient.system_one(state, questions)` takes input text and typed questions (`Choice`, `Score`, `Noul`) and returns answers with a predicted value, confidence, and probability distribution per question. It has no chat or tool use. Support may need a new abstraction for decision models, and may also be offered to agents as a tool. The SDK must be an optional extra, loaded only when used, and listed in the README.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A caller can ask Jev classification, score, and yes/no questions through numpty and get answers with confidences
- [ ] #2 An agent can use Jev decisions (for example through a tool)
- [ ] #3 `typesafe-sdk` is an optional extra listed in the README; importing numpty does not load it
- [ ] #4 Tests run offline
- [ ] #5 Public API is documented
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 tests pass
- [ ] #2 docstrings are up to date
<!-- DOD:END -->
