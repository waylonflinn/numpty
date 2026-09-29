---
id: doc-002
title: fastaudit notes
type: other
created_date: '2026-09-25 22:30'
updated_date: '2026-09-29 20:49'
---
# fastaudit notes

Facts about fastaudit that apply to NUMP-008 to NUMP-011. Source: the repository at commit `5acdce1` (2026-09-21), and a probe script run on Python 3.12 with pandas. fastaudit is about 370 lines of Python, Apache-2.0, and depends on fastcore.

## Threat model

fastaudit stops accidental damage by code that an LLM writes. It does not stop adversarial code. Its README says so, and it recommends a subprocess, container, VM, or OS-level policy for adversarial code. It trusts the process, the user account, and the existing filesystem layout, including symlinks.

## API

```python
audit = mk_audit(roots, before_deny=None, on_call=None, data=None,
                 monitor_calls=True, allow_imports=())
with audit():
    ...  # checks apply only inside the context
```

- The first `mk_audit` call installs one process-wide audit hook. A hook cannot be removed after it is installed.
- A `ContextVar` holds the active configuration. Checks apply only while a context is active, and they follow async tasks correctly.
- Each `mk_audit` call has its own configuration. Different tool calls can use different policies, one at a time.
- Contexts do not nest. Entering a context of a different configuration inside an active context raises the `audit_perms.set_config` event, which fastaudit denies. The same configuration can enter again. A `before_deny` callback can allow the event, and then the inner configuration replaces the outer one. It does not narrow it.
- A `mk_audit` call inside an active context is also denied. Make each configuration before you enter a context.
- `roots` is a flat list of directories. Each root includes its full tree. The root `'.'` means the current directory at the time of each check. `None` removes path checks. An empty list allows no paths.

## What it checks

| Area | Behavior |
|---|---|
| Reads | Not checked. `open` in read mode, `listdir`, `scandir`, and glob are always allowed. |
| Writes | `open` in a write mode (`w`, `a`, `x`, `+`), remove, rename, move, copy, rmtree, mkdir, chmod, sqlite, and tempfile. The parent directory must be in a root. Paths go through `realpath`. |
| Append | Treated the same as write. |
| Move, rename, link | Both paths are checked. |
| Subprocess | Denied. |
| Network | `socket.connect` is denied by default. DNS lookups are allowed. |
| ctypes | Denied. |
| Threads | Denied, except the asyncio executor thread. |
| Environment | Most changes are allowed. Changes to sensitive variables (`PATH`, `HOME`, `PYTHON*`, and others) are denied. |
| Unknown events | Denied. |

A denial raises `PermissionError` with the event name, its arguments, and the call chain. numpty already converts tool exceptions to error results, so the model gets this message.

## Native call monitoring

On Python 3.12 and later, fastaudit uses `sys.monitoring` to see calls into C extensions. numpty requires Python 3.12, so this is available.

- A native call from a package that is not on the safe list raises an event, which fastaudit denies.
- The safe list includes numpy, pandas, PIL, matplotlib, orjson, and pydantic-core. Packages can add themselves through an entry point.
- pyarrow is not on the list. Thus `DataFrame.to_parquet` is blocked, not written through pyarrow C++ I/O without a check. pyarrow reads are also blocked.
- The monitoring cost applies only while a context is active.
- fastaudit uses `sys.monitoring` tool id 3. This id does not conflict with debuggers, coverage, or profilers.

## `before_deny`

fastaudit calls `before_deny(event, args, frame, msg, data, calls)` before it raises for a blocked operation. A true return value allows the operation. An exception from the callback goes to the caller. The README describes it as the host policy hook, for trusted tools that need more access.

A probe script used `mk_audit((), before_deny=cb)`. With no roots, every write event goes to the callback. The callback allowed write in directory A and append only in directory B. Results:

| Action | Result |
|---|---|
| Write in A | Allowed |
| Append in B | Allowed |
| Write (`w`) in B | Denied |
| Write in C | Denied |
| Rename from A to C | Denied |
| pandas `to_csv` to A, then to C | Allowed, then denied |
| Read in C | Allowed. Reads never go to the callback. |

Thus the callback can apply a different policy to each directory, for writes only. It can see the open mode, so it can separate append from overwrite. It can see the path, so it can limit a scope to the current directory only.

Costs of this approach:

- The callback gets the raw CPython event and its arguments. It does not get the paths that fastaudit extracted. numpty must map each event to its paths again, or import private fastaudit tables.
- fastaudit path checks then do nothing useful. fastaudit still gives the hook, the context scope, default deny, and native call monitoring.
- Imports inside the context send events to the callback. The pandas import sent `ctypes.dlopen` and `os.mkdir`. Denial was harmless in the probe. The callback needs a clear rule for these, or numpty must import modules before it enters the context.

## Probe results (2026-09-29)

- No segmentation fault with pandas writes under `sys.monitoring` on CPython 3.12, 3.13, or 3.14. Source: the Q7 probe and the numpty test suite.
- pyarrow breaks under native call monitoring. `to_parquet` is denied. pandas 3 uses pyarrow for strings when pyarrow is installed, so string operations can also fail. numpty does not add pyarrow to its dev dependencies.
- CPython 3.14 raises a new event, `_posixsubprocess.fork_exec`, when `subprocess` starts a process. A policy that allows processes must allow this event too.

## Known limits

- Reads are not checked. With network access blocked, tool output is still a way to leak data.
- There is one permission level for all roots.
- Existing symlinks and file descriptors that are already open are trusted.
- Code in the same process can change the hook state on purpose, for example through `gc` or frame inspection. An LLM does not do this by accident.
- The fastaudit tests skip a case where `sys.monitoring` with pandas can crash CPython 3.13 with a segmentation fault. numpty must test with the Python versions it supports.
- The project is young. The first commit is from about April 2026. Pin a version range and read the changelog before an upgrade.

## Effect on the tasks

- **NUMP-008.** Use `mk_audit` roots as designed, for coarse write limits. Make fastaudit the optional extra `numpty[security]`, imported lazily.
- **NUMP-010.** Candidate upstream issues: read roots, current directory versus tree, append mode, and per-root permissions or structured paths in `before_deny`.
- **NUMP-011.** Two possible ways to close the gaps: a second audit hook that only narrows, or a `before_deny` policy with no roots. Both need a map from each event to its paths. Choose at task time.
