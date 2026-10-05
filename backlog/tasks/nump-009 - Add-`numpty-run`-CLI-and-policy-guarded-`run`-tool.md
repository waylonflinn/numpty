---
id: NUMP-009
title: Add `numpty run` CLI and policy-guarded `run` tool
status: Planning
assignee:
  - '@claude'
created_date: '2026-09-25 22:07'
updated_date: '2026-10-01 20:41'
labels: []
dependencies:
  - NUMP-008
documentation:
  - backlog/docs/doc-001 - Prior-art-limits-on-agent-run-code.md
  - backlog/docs/doc-002 - fastaudit-notes.md
  - backlog/docs/doc-003 - Harness-command-approval-and-numpty-run.md
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Agreed in planning (2026-09-30/10-01). Amended 2026-10-01 after pre-implementation review. Supersedes NUMP-001.

BLOCKED: CLI option semantics (slice 4) wait for a resolution of the allowlist-widening issue. See doc-003. Slices 1-3 and 5 do not depend on it.

Architecture
- One code path: `numpty run` (CLI) and `RunTool` both call `run(code, policy, location, timeout) -> subprocess.CompletedProcess`, which spawns `sys.executable -P -u -c "from numpty.run import _child; _child()" <policy names>` with the code on the child's stdin, `cwd=location`, `start_new_session=True`.
- `-P`: the location is not on `sys.path` while the bootstrap imports numpty and fastaudit. Without it, code under FS_WRITE_LOCATION can write `numpty/` or `fastaudit.py` (or shadow a stdlib module the bootstrap imports) into the location, and the next run imports it with no checks. Probe 2026-10-01 confirmed the shadowing. `_child` inserts the location (`""`) at `sys.path[0]` after it builds the policy and before `exec`, so local imports still work, under the policy.
- `-u`: output written before `os._exit` or a kill is not lost.
- Audit hooks do not cross a process boundary, so the child rebuilds the policy with `Policy.from_names(argv)` and enters `enforcement()` itself. Probe (2026-09-30): pandas/numpy import and write inside the active policy in a child; denials give the fastaudit reason.
- Exit codes fixed in `run`: 0 ok, 1 code raised (traceback trimmed to `<run>` frames), 124 timeout (parent kills the child's process group, stderr `[timed out after Ns]`), 126 policy denied (stderr `PermissionError: <reason>`), else the code's own exit.
- 126 only for a fastaudit denial: a `PermissionError` with `errno is None`. An OS `PermissionError` (errno set, e.g. EACCES) takes the exit-1 path.
- Timeout: the child is a session leader. On timeout the parent kills the whole process group, so grandchildren under PROC_UNRESTRICTED do not survive.
- Defaults match `Policy()`: READ only, no writes, in the tool. (CLI defaults: see BLOCKED.)
- `RunTool` inherits the agent policy, takes no location (NUMP-015 decides the agent working directory). `Agent(policy=None)` -> child unrestricted.
- Policy wire format is `names()` alone: `monitor_calls` becomes `Process.C_EXTENSIONS` so nothing travels outside the flags.
- Guardrail, not sandbox: child inherits env and interpreter. NUMP-012 wraps the same spawn.

Slices
1. `Policy.Process.C_EXTENSIONS` (policy.py): add member; remove `monitor_calls` kwarg from `__init__`/`from_names`; `_fastaudit_enforcement` passes `monitor_calls = C_EXTENSIONS not in process`; UNRESTRICTED implies it. The process-slot check in `_fastaudit_enforcement` (`elif flags: raise`) must ignore C_EXTENSIONS. Docstring names fastaudit's safe list (numpy, pandas, PIL, matplotlib, orjson, pydantic-core). README limit bullet. Tests: names round trip; monkeypatch `fastaudit.mk_audit` to capture `monitor_calls`; C_EXTENSIONS alone in the process slot does not raise.
2. `numpty/run.py`: `run(code: str, policy: Policy | None = None, location: str | None = None, timeout: float = 30) -> CompletedProcess` (policy None -> Policy(); location None -> cwd, expanduser). Uses Popen + communicate(timeout) + `os.killpg` on timeout. `_child()`: from_names(argv), read stdin, register the code in `linecache` under `<run>` (so traceback lines show source), `sys.path.insert(0, "")`, `exec(compile(code, "<run>", "exec"), {"__name__": "__main__"})` inside enforcement; PermissionError with errno None -> 126; other Exception -> trimmed traceback, exit 1; SystemExit propagates. Trim: drop leading frames until the first `<run>` frame; a SyntaxError has none, so the traceback can be empty. Format tracebacks outside enforcement. `class RunTool(Tool)`: name "run", parameters {code: string}, `__init__(timeout=30, max_output=10_000)`, description built from Python version/timeout/no stdin/no state, `run(arguments, policy=None) -> str` in ShellTool's report format via a shared private `_report(p, max_output)` in tools.py (ShellTool timeout becomes CompletedProcess(124)). `_report` changes ShellTool's timeout output; update `test_shell_tool_timeout` (tests/test_tools.py:78) or special-case 124, decide in the slice. Export `RunTool` from numpty (not the module-level `run`: `numpty.run` is the module).
3. `Agent.run`: `isinstance(tool, RunTool)` -> `tool.run(args, policy=self.policy or Policy.UNRESTRICTED)` outside enforcement (NOTE: special case until NUMP-013); others unchanged.
4. `numpty/cli.py` `main(argv=None) -> int`, `[project.scripts] numpty = "numpty.cli:main"` (needs `uv sync`). Subcommand `run`. Decided: the permission option is `-p/--permission`; `--policy` is reserved for a future concrete policy concept. Option semantics (defaults, repeats, location, timeout) BLOCKED on doc-003. Policy/location errors -> `parser.error` (exit 2). Reads stdin, calls `run`, passes stdout/stderr/exit code through.
5. Docs: README "Running code" (CLI examples, RunTool example, exit codes, guardrail-not-sandbox); regenerate docs/ with griffonner incl. RunTool page. README states: code can itself exit 124/126 (or 2 from the CLI) and look like a timeout/denial; code that catches a denial (`except Exception`) exits 0; packages that write a cache on first import (e.g. matplotlib) can fail under a no-write policy, and each call is a fresh process; for allowlist rules in Claude Code, end with ` *` (space, star).

Tests (tests/test_run.py, real subprocesses, importorskip fastaudit, short timeouts ~0.5s): run ok / write outside denied 126 with reason / write in location allowed under FS_READ|FS_WRITE_LOCATION / timeout 124 / timeout kills a grandchild under UNRESTRICTED / os._exit(3) -> 3 with prior print kept / 1/0 -> 1 without bootstrap frames, with source line / SyntaxError -> 1 / OS PermissionError (chmod 0o500 dir, write under UNRESTRICTED) -> 1 not 126 / `fastaudit.py` and `numpty/` in location do not run before enforcement / local module in location importable / UNRESTRICTED can spawn. RunTool: report format, [exit 126], truncation, standalone default Policy(). Agent via ScriptedModel: Policy()+RunTool spawns, denial text in result, policy=None -> unrestricted child. CLI main(): passthrough, exit codes, bad name -> SystemExit(2), missing location dir -> 2; option-semantics tests follow the doc-003 resolution.

Out of scope: --monitor-calls / --no-monitor-calls flag, python -m numpty, Tool.run(**kwargs) contract change (rejected: model-supplied names would collide with `policy`), Agent location (NUMP-015), extensions-list property (NUMP-014), `-c CODE` option for Codex allowlisting (candidate follow-up, doc-003).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-01: AWAITING RESOLUTION of the CLI allowlist-widening issue before implementation. Harness approval checks only a command prefix (Claude Code: text, Codex: words), so a repeated -p/-l or an omitted option appended after an approved prefix can widen the policy. Research and candidate design (full policy required, one definition per dimension) in doc-003. Plan amended with the non-CLI review fixes (-P bootstrap, errno discriminator for 126, process-group kill, -u, traceback details, test additions).

2026-10-01: Observed in the desktop app: 'Always allow' saves program+subcommand prefix rules (e.g. Bash(backlog doc *)), so it likely saves Bash(numpty run *); some prompts offer only Allow/Deny. Direction: best-effort CLI design first, then iterate on tests in Claude Code and Codex. User to review doc-003 and revisit.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-10-01 15:32
---
Plan ready for review
---

author: @claude
created: 2026-10-01 20:21
---
Awaiting resolution of the CLI allowlist-widening issue (doc-003). Plan amended with the other review fixes; slice 4 option semantics blocked.
---
<!-- COMMENTS:END -->
