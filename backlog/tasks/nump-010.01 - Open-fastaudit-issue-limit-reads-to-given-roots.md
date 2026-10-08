---
id: NUMP-010.01
title: 'Open fastaudit issue: limit reads to given roots'
status: Planning
assignee:
  - '@claude'
created_date: '2026-10-06 22:53'
updated_date: '2026-10-06 22:58'
labels: []
dependencies: []
references:
  - 'https://github.com/AnswerDotAI/fastaudit'
documentation:
  - doc-002 - fastaudit notes
parent_task_id: NUMP-010
type: chore
ordinal: 21000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
fastaudit does not check reads: open in read mode, listdir, scandir, and glob are always allowed, and reads never reach before_deny (doc-002). numpty's policy model (NUMP-008) has a read permission with scopes, so numpty cannot enforce it through fastaudit today. With network denied, reads plus tool output are the remaining exfiltration channel. Ask upstream for read roots before numpty builds a local read hook (NUMP-011). The issue should describe the change that a later PR from us would make. Posting is outward-facing: the user reviews and approves the draft before it is posted.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A draft issue describes the problem, the numpty use case, and the proposed change (read roots, or read events delivered to before_deny)
- [ ] #2 The user approves the draft before it is posted
- [ ] #3 The issue URL and posting date are recorded in NUMP-011
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 issue is posted on the fastaudit repo
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Draft the issue from the fastaudit 0.2.10 source (chk in core.py, _audit_allow) and doc-002. Draft is in the task notes.
2. User reviews the draft. Revise until approved.
3. Post with gh issue create on AnswerDotAI/fastaudit, label enhancement if the repo allows it.
4. Record the issue URL and posting date in NUMP-011 notes and in this task.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Draft issue (v1):

# Check reads against roots (opt-in `read_oks`)

## Problem

fastaudit checks writes against `oks`. It does not check reads. In `chk`, `open` in a read mode returns before the path check:

```python
if isinstance(mode,str) and not set('wax+') & set(mode): return
if mode is None and not flags & write_flags: return
```

`os.listdir`, `os.scandir`, `os.walk`, `os.fwalk`, `glob.glob`, `pathlib.Path.glob`, `pathlib.Path.rglob`, and `pathlib.Path.walk` are in `_audit_allow`. So reads never reach `deny`, and a host cannot add a read check in `before_deny` or a `fastaudit_audit_hook` either.

## Use case

[numpty](https://github.com/waylonflinn/numpty) runs tool calls from local LLMs inside a fastaudit context. The network is denied. Tool output still goes to the model, and from there to the user or a remote provider. So read-then-print is the leak that remains: the model opens `~/.ssh/id_rsa` or a `.env` outside the project, and the content leaves in the response. This is accidental overreach, inside the stated threat model. A small model reads a config file in the home directory because it is "nearby". numpty has read scopes in its policy (current directory, current tree, everywhere) that it cannot enforce today.

## Proposed change

Add `read_oks=None` to `mk_audit`. `None` keeps the current behavior. When it is set:

1. Check `open` in a read mode against `read_oks` with `ok_path`. Read mode is a `str` mode without `wax+`, or `mode is None` with no write flags.
2. Check the listing events above against `read_oks`. The path is `args[0]`. Remove them from `_audit_allow` when `read_oks` is set.
3. Send denials through `deny`, so `before_deny` and audit-hook entry points see read events the same way they see writes.
4. Treat `oks` as readable too. A write root that cannot be read is not useful. Effective read roots are `oks` plus `read_oks`.

`.` keeps its meaning: the current directory at the time of each operation.

### Imports

`import` reads `.py` and `.pyc` files through the `open` event with mode `'r'` (checked on CPython 3.13 with an audit hook). Read roots must not block the interpreter. Two options:

- (a) Always allow reads under `sys.prefix`, `sys.base_prefix`, and the entries of `sys.path`.
- (b) Allow `open` while the import system is on the stack, like `importing_allowed_module` does for `allow_imports`.

(a) is one `startswith` test per event and also covers data files that packages read from site-packages (certifi, locale data). I would start with (a). Reads of `/dev/null`, `/etc/localtime`, and similar can go through `before_deny`, since reads reach it after this change.

## Alternative

A smaller change: route read events to `before_deny` only, with no root check. Hosts then write the policy. The `read_oks` form matches the existing API and is the check most hosts want, so I propose it first.

I can open a PR for this.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-10-06 22:58
---
Plan ready for review
---
<!-- COMMENTS:END -->
