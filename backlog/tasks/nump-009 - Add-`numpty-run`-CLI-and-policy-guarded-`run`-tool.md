---
id: NUMP-009
title: Add `numpty run` CLI and policy-guarded `run` tool
status: To Do
assignee: []
created_date: '2026-09-25 22:07'
updated_date: '2026-09-25 22:31'
labels: []
dependencies:
  - NUMP-008
  - NUMP-001
documentation:
  - backlog/docs/doc-001 - Prior-art-limits-on-agent-run-code.md
  - backlog/docs/doc-002 - fastaudit-notes.md
type: feature
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Let an agent run Python under a permissions policy (NUMP-008). There are two entry points on one code path:
- CLI: `numpty run --policy <flags>`, with the code on stdin. For agents such as Claude Code or Codex.
- `run` PythonTool (name is tentative): the same function for agents that use the numpty library.

Purpose: a human reviewer approves a short command and a simple policy, instead of reading a long script. A reviewer can also allowlist a command pattern for a given policy.

The code runs in a subprocess, not with `exec` in the agent process. Reasons: a timeout can stop it, a crash does not kill the agent, the code cannot change agent state, and a later OS sandbox applies to both entry points. Costs: startup time per call, and no state kept between calls.

Builds on `run_python` (NUMP-001).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Running `numpty run --policy <flags>` runs Python from stdin under the policy and returns stdout, stderr, and the exit code
- [ ] #2 CLI policy values use the same names as the `Policy` flags and can be combined
- [ ] #3 The `run` tool and the CLI share one entry point
- [ ] #4 Code runs in a subprocess with a timeout; a timeout or crash returns a clear message
- [ ] #5 A denied operation returns the reason for the denial
- [ ] #6 Tests cover allowed, denied, and timeout cases for both the CLI and the tool
- [ ] #7 Documentation states that the policy is a guardrail, not a sandbox
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 tests pass
- [ ] #2 docstrings are up to date
<!-- DOD:END -->
