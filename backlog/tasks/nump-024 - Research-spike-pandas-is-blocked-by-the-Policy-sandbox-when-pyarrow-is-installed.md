---
id: NUMP-024
title: >-
  Research spike: pandas is blocked by the Policy sandbox when pyarrow is
  installed
status: To Do
assignee: []
created_date: '2026-10-08 19:56'
labels:
  - research
  - policy
dependencies: []
references:
  - src/numpty/policy.py
  - tests/test_policy.py
documentation:
  - doc-002 - fastaudit notes
type: spike
ordinal: 27000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found in NUMP-021 (2026-10-08). With `pyarrow` in the venv, 5 cases of `tests/test_policy.py::test_enforcement` fail (the `pandas` and `pandas_outside` actions under the write policies): `pd.DataFrame({"x": [1]})` inside `Policy.enforcement()` raises `PermissionError: Audit: fastaudit.call blocked in sandbox with args: (pandas.core.arrays.string_arrow.ArrowStringArray._from_sequence, pyarrow.lib.large_string)`. pandas 3.0.6 uses Arrow-backed strings when pyarrow is installed. fastaudit (0.2.10) call monitoring denies native callees whose module is not stdlib or in the `fastaudit_safe_native` entry-point group, which fastaudit itself registers for pandas, numpy, PIL, matplotlib, orjson, pydantic_core and others, but not pyarrow. The Policy docstring documents pyarrow as blocked (`DataFrame.to_parquet`) and offers `Process.C_EXTENSIONS`, but that limit now reaches plain pandas, which the docstring lists as working. Most data environments have pyarrow, so pandas under any restrictive Policy likely fails for real users. NUMP-021 avoided the issue by keeping pyarrow out of the dev group (PEP 723 metadata on `scripts/eval/td_*.py`), so the test suite does not currently exercise this case. Relevant code: `src/numpty/policy.py` (`_fastaudit_enforcement`, `monitor_calls`), fastaudit `core.py` (`call_cb`, `safe_native`, `on_call`, `fastaudit_monitor_hook`). Decision expected: the fix approach for a follow-up implementation task.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Which pandas operations call pyarrow native code when pyarrow is installed (construction, string ops, I/O), and does the failure need pyarrow or only a pandas setting such as `future.infer_string`
- [ ] #2 What file and network access pyarrow native code performs without Python audit events (parquet/feather writers, `pyarrow.fs`, S3/GCS, flight), and so what allowing pyarrow as safe native would let past the write guard
- [ ] #3 What fastaudit offers to allow pyarrow narrowly: `fastaudit_safe_native` entry point registered by numpty, `on_call` or a `fastaudit_monitor_hook` that allows only some `pyarrow.lib` callees or only calls made from pandas, and whether an upstream fastaudit change is the better route (relate to NUMP-010/NUMP-011)
- [ ] #4 What numpty can do without fastaudit changes: force Python string storage inside enforcement, ship an allowlist, or keep the limit and document it, with the tradeoff of each against the default-deny design
- [ ] #5 How the test suite covers both environments (pyarrow present and absent) so the regression is caught
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 doc records reasoning and sources
- [ ] #2 decision record produced
<!-- DOD:END -->
