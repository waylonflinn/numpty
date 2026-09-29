---
id: NUMP-008
title: Define a permissions policy model backed by fastaudit
status: Done
assignee:
  - '@claude'
created_date: '2026-09-24 21:31'
updated_date: '2026-09-29 21:22'
labels: []
dependencies: []
references:
  - 'https://github.com/AnswerDotAI/fastaudit'
  - 'https://peps.python.org/pep-0578/'
documentation:
  - backlog/docs/doc-001 - Prior-art-limits-on-agent-run-code.md
  - backlog/docs/doc-002 - fastaudit-notes.md
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Define a permissions policy that limits what tools can do, mainly on the file system. Today no limits exist: file functions accept any path, and `ShellTool` has full shell access to everything the current user can access, with no sandbox.

This is stage 1. Enforcement uses fastaudit (Answer.AI), an in-process guardrail based on Python audit hooks. It is an optional dependency (`numpty[security]`), loaded lazily. Stage 1 exposes only the permissions that fastaudit can enforce. Gaps are requested upstream (see the upstream issues task); a fallback task fills them locally if upstream does not respond in time.

Threat model: a guardrail against accidental overreach by a model, including low-reliability local models. It is not a hard boundary against adversarial code. Documentation must say so. An OS-level sandbox is later work.

Policy model:
- Flags combine bitmask style, for example `Policy.READ | Policy.WRITE_CURRENT_TREE`. Flag names state what is enabled, never what is disabled.
- Final shape: read, append, and write permissions, each with its own scope (current directory only, tree rooted at the current directory, wider). Design the class for this shape now. Stage 1 accepts only what fastaudit enforces: read everywhere (fastaudit does not check reads), write in the current tree or given roots, and unrestricted. Other combinations raise a clear error. They are never silently widened.
- Flag names must stay true when later stages add read scopes. Users will put them in allowlists (for example `numpty run --policy ...` in Claude Code), so a rename is a breaking change.
- Network access and subprocesses are denied for every policy except unrestricted.

Known gap: stage 1 does not check reads. With network denied, tool output sent to the model provider is the remaining exfiltration channel (for example, read a credentials file and print it). Document this.

Enforcement notes:
- `Agent` enters the policy context around each tool call, not around model queries.
- If the policy restricts anything and fastaudit is not installed, raise `ImportError` with the install hint. Fail closed.
- Tools that start processes (`ShellTool`) require unrestricted. `Agent` raises at construction otherwise, so the model does not get a denial on every call.
- fastaudit denies thread creation inside the context. Document this.
- Pin a fastaudit version range: the project is young, and its tests note a `sys.monitoring` segfault risk with pandas on CPython 3.13.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Policy flags combine with `|`, and each flag name states an enabled permission
- [x] #2 The policy class supports read, append, and write, each with its own scope; combinations the backend cannot enforce raise a clear error
- [x] #3 Stage 1 flags cover read everywhere, write in the current tree, and unrestricted
- [x] #4 fastaudit is the optional extra `numpty[security]`, imported lazily; a restrictive policy without it raises `ImportError` that names the extra
- [x] #5 `Agent` applies the policy to every tool call; a denied action returns an error result to the model
- [x] #6 Network access and subprocesses are denied unless the policy is unrestricted
- [x] #7 `Agent` with `ShellTool` and a policy that is not unrestricted raises at construction
- [x] #8 Tests cover allowed and denied actions for each flag, including `..` and symlink path escapes and a pandas write
- [x] #9 Public API is documented, including the threat model, unchecked reads, and the thread restriction
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 tests pass
- [x] #2 docstrings are up to date
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Design agreed in session 2026-09-29. Nested flags, three subsystems, fastaudit backend.

1. pyproject: add extra `security = ["fastaudit>=0.2.10,<0.3"]`, add it to `all`. Add `fastaudit` and `pandas` to the dev group. Do not add pyarrow (pandas 3 arrow strings break under native call monitoring).
2. `src/numpty/policy.py`, class `Policy`:
   - Nested `enum.Flag` classes: `Filesystem` (READ, READ_LOCATION, READ_LOCATION_TREE, APPEND, APPEND_LOCATION, APPEND_LOCATION_TREE, WRITE, WRITE_LOCATION, WRITE_LOCATION_TREE, UNRESTRICTED), `Network` (READ, READ_LOCATION, READ_LOCATION_TREE, WRITE, WRITE_LOCATION, WRITE_LOCATION_TREE, UNRESTRICTED), `Process` (UNRESTRICTED). Each UNRESTRICTED is its own bit.
   - `__init__(filesystem=Filesystem.READ, network=Network(0), process=Process(0), monitor_calls=True)`. Builds `_FastauditBackend` when any slot is not UNRESTRICTED. Raises ImportError naming `numpty[security]` if fastaudit is missing, ValueError if the backend cannot enforce the combination. Never widens.
   - `Policy.UNRESTRICTED`: class attribute, all three slots UNRESTRICTED, set after the class body. Needs no fastaudit.
   - `enforcement()`: returns a fresh context manager. `nullcontext()` when nothing is restricted.
   - `names()` -> ["FS_READ", ...] with prefixes FS_, NET_, PROC_; `from_names(names)` classmethod, accepts "UNRESTRICTED" for the whole policy.
3. `_FastauditBackend` (same module, private): the only place that imports fastaudit. Maps flags to `mk_audit(roots, before_deny, monitor_calls)`:
   - Filesystem READ -> roots (); READ|WRITE_LOCATION_TREE -> ['.']; READ|WRITE or UNRESTRICTED -> None; empty slot, any APPEND*, READ_LOCATION*, WRITE_LOCATION alone -> ValueError.
   - Network empty -> deny (fastaudit default); UNRESTRICTED -> before_deny allows prefixes `socket.`, `http.client.`; other flags -> ValueError.
   - Process empty -> deny; UNRESTRICTED -> before_deny allows `subprocess.`, `os.system`, `os.exec`, `os.posix_spawn`, `os.spawn`, `_thread.`. Verify the prefix list against the CPython audit event table during implementation.
4. `Agent`: `policy: Policy | None = None` kwarg. `run()` wraps `tool.run` in `with policy.enforcement():`. Private `_check_policy()` in the constructor raises ValueError when a ShellTool is present and `Process.UNRESTRICTED` is not in the policy. Tool base class unchanged.
5. Export `Policy` from `numpty/__init__.py`.
6. Tests. `tests/test_policy.py`: flag combination and names round trip; each enforceable combination allows and denies the expected actions (write_file, append_file, pandas to_csv, `..` escape, symlink escape, subprocess, socket, thread); every unenforceable combination raises ValueError; missing fastaudit raises ImportError naming the extra (monkeypatch sys.modules). `tests/test_agent.py`: denied tool call returns an error result; ShellTool with a restricted policy raises at construction; policy=None keeps current behavior. Build every Policy outside an active context (fastaudit denies creation inside one).
7. Docs: docstrings on Policy, backend, Agent changes. README section "Permissions": threat model (guardrail, not a sandbox), reads not checked and the tool-output leak, threads denied, pyarrow caveat, nested agents cannot enter a second context, ShellTool needs Policy.UNRESTRICTED. Regenerate griffonner docs; check nested class rendering.
8. Correct doc-002: contexts do not nest by default, an allowed inner context replaces the outer. Add the Q7 probe results (no segfault on 3.12 or 3.13, pyarrow breakage under monitoring).
9. Follow-up task: general tool-to-policy compatibility check (tool declares the Policy it needs, Policy defines subset comparison).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented plan steps 1-9. Deviations: backend is a private function `_fastaudit_enforcement` (one call site, no state) instead of a `_FastauditBackend` class. Redundant flags are accepted (READ|READ_LOCATION, READ|WRITE|WRITE_LOCATION_TREE, APPEND scope <= WRITE scope: WRITE includes append). CPython 3.14 adds audit event `_posixsubprocess.fork_exec`, added to process prefixes. Class template now renders nested classes (Policy.Filesystem etc.). Fixed pre-existing griffe parse bug in Agent.run Returns (continuation lines split into items). Tests: 159 pass on 3.12, 3.13, 3.14; core imports and tests pass without fastaudit. Follow-up: NUMP-013. Docstrings are drafts awaiting review.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-09-29 20:38
---
Plan ready for review
---

author: @claude
created: 2026-09-29 20:44
---
Plan approved by @waylonflinn in session
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added `Policy` (src/numpty/policy.py): nested `Filesystem`, `Network`, `Process` flags, fastaudit enforcement via the optional `numpty[security]` extra, `names()`/`from_names()`, `Policy.UNRESTRICTED`. `Agent` takes `policy=`, enforces it around each tool call, and rejects `ShellTool` without `Process.UNRESTRICTED` at construction. README Permissions section documents the threat model, unchecked reads, thread denial, pyarrow, and nesting. doc-002 corrected. Verified: 159 tests pass on CPython 3.12, 3.13, 3.14 (allowed/denied matrix per flag incl. `..`, symlink, pandas writes, subprocess, socket, threads); core imports and passes without fastaudit. Docstrings reviewed and approved by @waylonflinn. Follow-ups: NUMP-013, NUMP-014.
<!-- SECTION:FINAL_SUMMARY:END -->
