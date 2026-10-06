---
id: NUMP-012
title: Add an OS-level sandbox backend for policies
status: To Do
assignee: []
created_date: '2026-09-25 22:08'
updated_date: '2026-10-06 15:27'
labels: []
dependencies:
  - NUMP-009
references:
  - 'https://github.com/anthropic-experimental/sandbox-runtime'
documentation:
  - 'doc-001 - Prior art: limits on agent-run code'
  - doc-002 - fastaudit notes
priority: low
type: feature
ordinal: 12000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The fastaudit guardrail (NUMP-008) is in-process and does not stop adversarial code. Add a backend that applies the same `Policy` at the OS level to the subprocess that `numpty run` and the `run` tool start (NUMP-009): Seatbelt (`sandbox-exec`) on macOS, and Landlock with seccomp (or bubblewrap) on Linux. The kernel then enforces the policy, which also covers C extensions, ctypes, and child processes.

Known limits to resolve: the OS cannot enforce append-only writes; Landlock cannot express the current directory only; read-restricted policies must allow the interpreter, stdlib, site-packages, and virtual environment paths.

Optional, later work. Prior art: Codex CLI sandbox, Anthropic sandbox-runtime.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 On macOS, a policy runs the subprocess under a generated Seatbelt profile
- [ ] #2 A denied write from a C extension (for example pyarrow) is blocked
- [ ] #3 The CLI and tool interface do not change
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 tests pass
- [ ] #2 docstrings are up to date
<!-- DOD:END -->
