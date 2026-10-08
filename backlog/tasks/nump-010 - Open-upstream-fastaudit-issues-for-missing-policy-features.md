---
id: NUMP-010
title: Open upstream fastaudit issues for missing policy features
status: To Do
assignee: []
created_date: '2026-09-25 22:07'
updated_date: '2026-10-08 20:00'
labels: []
dependencies: []
references:
  - 'https://github.com/AnswerDotAI/fastaudit'
documentation:
  - 'doc-001 - Prior art: limits on agent-run code'
  - doc-002 - fastaudit notes
type: chore
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
numpty uses fastaudit to enforce its permissions policy (NUMP-008). fastaudit does not support some parts of the numpty policy model. Ask upstream for them with feature requests, before we build them locally.

Known gaps (the split into issues is decided at task time; one issue per gap is likely):
- Limit reads to given roots. fastaudit does not check reads. With network denied, reads plus tool output are the remaining exfiltration channel.
- Separate the current directory only from the tree rooted at it. fastaudit roots always include the full tree.
- Append mode: allow append and new files, but deny overwrite and truncate. fastaudit treats append as write.
- Possibly others found during NUMP-008.

Each issue should describe the change that a later PR from us would make (see the fallback task). Posting is outward-facing: the user reviews and approves each draft before it is posted.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Each gap has a draft issue that describes the problem, the use case, and the proposed change
- [ ] #2 The user approves each draft before it is posted
- [ ] #3 Issue URLs and posting dates are recorded in NUMP-011 (the fallback task)
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 tests pass
- [ ] #2 docstrings are up to date
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Candidate issue: per-root permission levels, or pass the operation kind and resolved paths to `before_deny`. Either makes fine-grained policy an intended use and removes the need for numpty to map events to paths. See doc-002.

Read-roots gap: issue posted 2026-10-08, https://github.com/AnswerDotAI/fastaudit/issues/28 (NUMP-010.01, Done). Current-directory-only and append-mode gaps still need issues.
<!-- SECTION:NOTES:END -->
