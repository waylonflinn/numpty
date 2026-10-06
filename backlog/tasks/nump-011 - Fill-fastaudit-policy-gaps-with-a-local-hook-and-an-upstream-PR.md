---
id: NUMP-011
title: Fill fastaudit policy gaps with a local hook and an upstream PR
status: To Do
assignee: []
created_date: '2026-09-25 22:08'
updated_date: '2026-10-06 15:27'
labels: []
dependencies:
  - NUMP-008
  - NUMP-010
documentation:
  - 'doc-001 - Prior art: limits on agent-run code'
  - doc-002 - fastaudit notes
type: feature
ordinal: 11000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Fallback for NUMP-010. Start this task only if the upstream fastaudit issues have no timely resolution: no maintainer acceptance within 3 weeks of posting, or a rejection.

Add a numpty audit hook that runs next to fastaudit. Python runs all audit hooks, and any hook that raises denies the operation, so this hook can only narrow what fastaudit allows. It adds:
- read scope checks
- append versus overwrite: allow append mode and new files; deny `w` mode and truncate where only append is allowed
- current directory only (no subdirectories) as a scope separate from the tree

Then enable the remaining `Policy` flags, so that read, append, and write each accept every scope. Existing flag names do not change.

Open a PR upstream, built from this code, that closes the open issues. When upstream releases the features, remove the local parts that it replaces.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Read, append, and write each accept the current directory only, the current tree, and wider scopes
- [ ] #2 The local hook only narrows: tests show that every fastaudit denial still applies
- [ ] #3 Append allows append mode and new files, and denies overwrite and truncate
- [ ] #4 Tests cover allowed and denied actions for each permission and scope
- [ ] #5 An upstream PR is opened after user approval, and it references the open issues
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 tests pass
- [ ] #2 docstrings are up to date
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Two possible ways to close the gaps: (1) a second audit hook that only narrows, or (2) `mk_audit((), before_deny=cb)`, where the callback is the full write policy (probe confirmed per-directory write and append rules). Both need a map from each event to its paths. Reads never reach `before_deny`, so read checks need a hook in both cases. Choose at task time. See doc-002.
<!-- SECTION:NOTES:END -->
