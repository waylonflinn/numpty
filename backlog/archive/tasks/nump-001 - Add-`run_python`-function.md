---
id: NUMP-001
title: Add `run_python` function
status: To Do
assignee: []
created_date: '2026-09-24 16:02'
updated_date: '2026-10-01 15:26'
labels: []
dependencies: []
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add a `run_python(code)` function to `numpty.functions` that runs Python code in a subprocess (`python -c`) and returns stdout and stderr. It generalizes `calculate`: the model writes real code instead of arithmetic strings. A stub existed in the source notebook (lesson_01b.py) and was left out of the initial library port.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Returns stdout of the executed code
- [ ] #2 Non-zero exit returns stderr and the exit code
- [ ] #3 Runs in a subprocess with a timeout; a timeout returns a clear message
- [ ] #4 Wraps cleanly as a `PythonTool` (typed, documented parameters)
- [ ] #5 Tests cover success, error, and timeout
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 tests pass
- [ ] #2 docstrings are up to date
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Superseded by NUMP-009 (2026-10-01): `run(code, policy, location, timeout)` in numpty/run.py plus `RunTool`. The policy-bearing function is not PythonTool-wrappable, so a Tool subclass replaces AC#4.
<!-- SECTION:NOTES:END -->
