---
id: NUMP-015
title: Add a working directory to Agent
status: To Do
assignee: []
created_date: '2026-09-30 23:24'
labels: []
dependencies:
  - NUMP-009
type: feature
ordinal: 15000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Agreed in the NUMP-009 planning session (2026-09-30). A run of `numpty run --location <dir>` scopes the policy and relative paths to one directory. A library agent has no equivalent: the policy's location scopes and relative paths in tools follow the process working directory, which the host program may change. `RunTool` (NUMP-009) takes no location of its own for this reason, so this task decides what a tool call's working directory is. Facts: `os.chdir` raises an audit event that fastaudit denies, so a directory change must happen outside `Policy.enforcement()`. A process-wide `chdir` at construction changes the host program, so a per-call change (`contextlib.chdir`) is the likely mechanism. NUMP-014 can then use the location for an absolute path in the policy description.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Agent takes an optional working directory; None means the process working directory
- [ ] #2 Relative paths in tool calls, location scopes in the policy, and the RunTool child all resolve to that directory
- [ ] #3 The host program's working directory is unchanged after a tool call
- [ ] #4 Tests cover an in-process tool and RunTool under a location that is not the process working directory
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 tests pass
- [ ] #2 docstrings are up to date
<!-- DOD:END -->
