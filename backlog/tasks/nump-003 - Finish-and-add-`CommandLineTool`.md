---
id: NUMP-003
title: Finish and add `CommandLineTool`
status: To Do
assignee: []
created_date: '2026-09-24 16:02'
labels: []
dependencies: []
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The source notebook (lesson_01b.py) had a `CommandLineTool` class that wraps one specific command-line program as a tool. It was left out of the initial library port because it is incomplete: it does not accept or store `parameters`, so models cannot render a tool definition for it. It also does not subclass `Tool`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Subclasses `Tool` and exposes `name`, `description`, and `parameters`
- [ ] #2 Renders as a tool definition with every provider model
- [ ] #3 Maps call arguments to the command line in a documented, tested way
- [ ] #4 Non-zero exit is reported to the model
- [ ] #5 Exported from `numpty` and included in generated docs
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 tests pass
- [ ] #2 docstrings are up to date
<!-- DOD:END -->
