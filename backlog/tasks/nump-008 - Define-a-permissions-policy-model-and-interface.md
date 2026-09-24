---
id: NUMP-008
title: Define a permissions policy model and interface
status: To Do
assignee: []
created_date: '2026-09-24 21:31'
labels: []
dependencies: []
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Define a simple permissions (policy) model and interface that limits what tools can do, mainly on the file system. Today no limits exist: file functions accept any path, and `ShellTool` has full shell access, with no sandbox, to everything the current user can access. That is one reason `ShellTool` was not used in the example notebook.

Initial ideas (not decided):
- Combine a tiered approach with a mix-and-match, bit-flag style approach.
- Separate permissions for read, append (non-destructive write), and write (destructive write).
- Scopes, from narrow to wide: the current directory only (no subdirectories), the tree rooted at the current directory, and wider scopes. Each permission (read, append, write) can expand its scope on its own.
- Example tiers: read only in the current tree, then append in the same scope, then full write in the same scope.
- A final "unrestricted" tier that skips the policy. `ShellTool` belongs in this tier.
- Python is the primary way to add tools in this library, so the policy can likely be enforced completely for all Python-based tools.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A policy expresses read, append, and write permissions, each with its own scope
- [ ] #2 Scopes include current directory only and the tree rooted at the current directory, and can expand beyond it
- [ ] #3 Named tiers exist for common combinations, including an unrestricted tier
- [ ] #4 Python-based file tools enforce the policy; a denied action returns an error result to the model
- [ ] #5 `ShellTool` requires the unrestricted tier
- [ ] #6 Tests cover allowed and denied actions for each permission and scope
- [ ] #7 Public API is documented
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 tests pass
- [ ] #2 docstrings are up to date
<!-- DOD:END -->
