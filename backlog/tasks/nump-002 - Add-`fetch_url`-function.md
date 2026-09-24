---
id: NUMP-002
title: Add `fetch_url` function
status: To Do
assignee: []
created_date: '2026-09-24 16:02'
labels: []
dependencies: []
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Add a `fetch_url(url)` function to `numpty.functions` that fetches a URL, strips HTML to text, and truncates the result. It gives the agent web access without a search API. Any HTTP dependency must be an optional extra, loaded only when the function is called (same pattern as `calculate` and `simpleeval`). A stub existed in the source notebook (lesson_01b.py) and was left out of the initial library port.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Returns page text with HTML markup removed
- [ ] #2 Output longer than a configurable limit is truncated with a visible marker
- [ ] #3 HTTP dependency is an optional extra, listed in the README; importing numpty does not load it
- [ ] #4 Wraps cleanly as a `PythonTool`
- [ ] #5 Tests run offline
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 tests pass
- [ ] #2 docstrings are up to date
<!-- DOD:END -->
