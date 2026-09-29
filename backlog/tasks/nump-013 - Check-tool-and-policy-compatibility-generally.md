---
id: NUMP-013
title: Tool and Policy Compatibility Check
status: To Do
assignee: []
created_date: '2026-09-29 20:49'
updated_date: '2026-09-29 21:22'
labels: []
dependencies:
  - NUMP-008
references:
  - src/numpty/agent.py
  - src/numpty/policy.py
ordinal: 13000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`Agent` rejects a `ShellTool` under a policy without `Policy.Process.UNRESTRICTED`, at construction, so the model does not get a denial on every call. This is a special case in `Agent._check_policy` (NUMP-008). Other tools that need more than a policy allows (network clients, process starters, writers) fail only at call time. A general check needs each tool to state the permissions it needs, and `Policy` to compare two policies. The earlier design rejected a single-purpose attribute on `Tool` (such as `needs_process`), so the tool must declare a `Policy` or an equivalent, not a flag for one subsystem.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `Policy` can tell if one policy allows everything that another policy allows
- [ ] #2 A tool can state the permissions it needs, and `ShellTool` does so
- [ ] #3 `Agent` raises at construction when a tool needs more than its policy allows
- [ ] #4 The `ShellTool` special case in `Agent` is removed
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 tests pass
- [ ] #2 docstrings are up to date
<!-- DOD:END -->
