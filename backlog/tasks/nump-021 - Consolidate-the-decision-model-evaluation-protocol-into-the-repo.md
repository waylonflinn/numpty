---
id: NUMP-021
title: Consolidate the decision-model evaluation protocol into the repo
status: Done
assignee:
  - '@claude'
created_date: '2026-10-08 14:47'
updated_date: '2026-10-08 19:50'
labels:
  - decision-models
dependencies: []
references:
  - 'https://github.com/fstandhartinger/jevbench'
  - 'https://huggingface.co/datasets/LocalLLaMA/typed-decisions'
documentation:
  - doc-008 - Decision model evaluation protocol
  - doc-005 - Local decision models for llama.cpp (NUMP-016)
  - doc-007 - Winnow-12B to a llama.cpp decision GGUF (NUMP-018)
  - >-
    decision-002 - Winnow-12B is served by upstream llama-server through
    metadata-only conversion (type nimble); Winnow for text accuracy
  - Clef-Flash for images
  - calibration
  - and throughput
type: chore
ordinal: 23000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Three spikes (NUMP-016, NUMP-016.01, NUMP-018) evaluated local decision models on saturn with the same procedure: JevBench public 231 items through the jevbench CLI with the typesafe adapter, the typed-decisions all/test split (400 cases, 2,000 decisions) through a scorer that measures accuracy, KL and Brier against the teacher distribution, warm latency for one and five questions, and sample distributions. The method is described in doc-005 and doc-007 and the tolerance rule is decision-002 item 4, but the scorer (`td_probe.py`), the sample script (`td_examples.py`) and the dataset parquet live only in session scratch directories under /private/tmp, and the JevBench clone and results live on saturn under ~/Build. The spike rule kept them out of the repo. They have now been reused on three models and are infrastructure, not probes. The next model evaluation (Quyet-1.0-Large) should be one command per set, not a reconstruction. Scope: scripts in the repo, a Backlog doc that states the protocol, and a durable home for the per-model results. Out of scope: `scripts/jev_xref.py` (the doc-006 watch script, kept uncommitted on purpose) and any change to numpty library code.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Scripts under `scripts/eval/` run from the Mac against the saturn router with a model id argument: the typed-decisions scorer, the distribution-sample script, and a JevBench run-and-summarize wrapper (or documented invocation of the jevbench CLI on saturn)
- [x] #2 The typed-decisions scorer reproduces the uniform baseline (KL 0.444, Brier 0.238) and the recorded clef-flash-9b-Q8, winnow-12b-Q8 and lev-4b-Q8 figures in doc-007 within rounding
- [x] #3 A Backlog doc "Decision model evaluation protocol" states the fixed sets and revisions (jevbench c6004e0 public files, typed-decisions all/test), each metric and its target (one-hot label for JevBench, teacher distribution for typed-decisions, ECE), the saturn settings (router, one request at a time, Q8_0 weights, q8_0 KV), the throughput method, the distribution-sample rows, and the tolerance rule from decision-002
- [x] #4 Per-model result summaries for the three models already measured are stored in a location the doc names, and a new model run adds one file without editing the scripts
- [x] #5 The doc lists what still lives only on saturn (jevbench clone, raw results, start8099.sh, models.ini presets) and how to recreate it
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 tests pass
- [x] #2 docstrings are up to date
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Findings (2026-10-08, nothing changed yet)

- Scratch scorer `td_probe.py` is byte-identical in the NUMP-016 and NUMP-018 sessions (3,410 bytes). `td_examples.py` (NUMP-018 review session) is the sample script. All three scratch copies of `td_test.parquet` have the same md5; the source is `LocalLLaMA/typed-decisions` revision d0e2f0c (2026-10-01), file `all/test-00000-of-00001.parquet`, 222,140 bytes, x-linked-etag 4f294f21...
- Scorer semantics to keep: accuracy of argmax (first key wins ties, hence the 0.269 uniform baseline vs the board's 0.308), KL(gold || model) with eps 1e-6, multi-class Brier as the sum of squared differences over the union of keys, uniform baseline computed from the gold alone. Warm p50 excludes the first request (cold). ECE is not computed today; the board publishes it.
- JevBench: `fstandhartinger/jevbench` c6004e0 is pure stdlib (pyproject has no dependencies, python >= 3.10), so it runs on the Mac. `typesafe` adapter: `--key-env ''` for no auth. Saturn runs used endpoint `http://127.0.0.1:4341` (router, clef and lev) and `http://127.0.0.1:8099` (manual server, winnow). `summarize --public-export` writes a 50 KB summary.json (accuracy, n_correct, brier_mean, ece{3}, macro_accuracy, ordinal_mae, latency{3}, per_family{18}, dataset_hash dc3995d8...).
- Saturn only: `~/Build/jevbench` clone, `~/Build/results/jevbench-{8099,clef-flash-9b-Q8,lev-4b-Q8}/`, `~/Build/start8099.sh` (manual verbose server, winnow GGUF, port 8099), `~/Build/gguf_add_decision.py`, `winnow_systemone.jinja`, `fork_prompt.py`, `venv-gguf`, `/opt/llama/config/models.ini` decision presets `lev-4b-Q8` (ctx 32768), `clef-flash-9b-Q8` (ctx/batch/ubatch 16384, mmproj), `winnow-12b-Q8` (ctx 8192); `[*]` defaults flash-attn, ngl 99, q8_0 KV, parallel 1.
- Repo: no pyarrow (pandas is a dev dep, parquet needs an engine). `/docs/` is gitignored (generated), so results cannot live there. `scripts/jev_xref.py` is untracked by request and stays so.

## Plan

1. Layout `scripts/eval/` (one shared module, three commands, data and results dirs):
   - `harness.py`: fixed constants (saturn URL, dataset repo/revision/sha256, jevbench repo/commit, workflows), `systemone(model, state, questions, base_url) -> (body, seconds)` over stdlib HTTP (sequential, no retries), `typed_decisions() -> list[case]` (download the pinned parquet to `scripts/eval/data/` on first use, verify sha256, read with pyarrow), metric functions `kl`, `brier`, `ece`, `argmax`, and `write_result(model, name, obj)`.
   - `td_score.py MODEL [--base-url]`: 400 cases, one request per case, 2,000 decisions. Writes `results/MODEL/typed_decisions.json` with the scratch keys plus `ece` in every aggregate (`all`, `uniform_baseline`, `by_type`, `per_question`).
   - `td_samples.py MODEL [--base-url]`: first test case per workflow; per-question distributions (keys, gold, model, gold label) and warm medians for one and five questions (5 and 3 repeats, as the scratch). Writes `results/MODEL/samples.json`.
   - `jevbench.py MODEL [--base-url] [--endpoint]`: clones jevbench at c6004e0 into `scripts/eval/data/jevbench/` on first use, runs `run` then `summarize` against the router with the typesafe adapter and `--key-env ''`, raw run under `scripts/eval/data/runs/jevbench-MODEL/`, copies `summary.json` to `results/MODEL/jevbench.json`.
   - `scripts/eval/results/<model-id>/` is the durable home (AC #4): three JSON files per model, a new model is a new directory. `scripts/eval/data/` is gitignored.
2. Deps: `uv add --group dev pyarrow`. jevbench needs nothing. Scripts run with `uv run scripts/eval/<cmd>.py <model>`.
3. Tests `tests/test_eval.py` (offline): metric functions on hand data (KL of equal dists 0, Brier of one-hot miss 2, ECE of a perfectly calibrated bin 0, argmax tie breaks on first key); every stored `typed_decisions.json` has uniform baseline KL 0.444 and Brier 0.238; the three recorded models match the doc-007 figures (acc, KL, Brier, by-type acc). pyproject `pythonpath` gains `scripts/eval`.
4. Backfill by re-running (this is the AC #2 verification): `td_score` and `td_samples` for clef-flash-9b-Q8, winnow-12b-Q8, lev-4b-Q8 (about 15 minutes of saturn time, sequential), `jevbench` for the three through the router from the Mac (about 10 minutes). The saturn originals stay where they are; the results README notes that doc-007's winnow JevBench row was measured on the manual 8099 server and that Mac-side jevbench latency includes the tailscale hop.
5. doc-008 "Decision model evaluation protocol": sets and revisions, metrics and targets (one-hot for JevBench, teacher distribution for typed-decisions, ECE on both), saturn settings, throughput method, sample rows, decision-002 item 4 tolerance, result location and file shapes, the one-command-per-set invocations, the saturn-only list and how to recreate it (clone, start8099.sh, presets). Link from doc-005 and doc-007 with a one-line pointer; NUMP-021 and NUMP-022 `--doc` entries get `doc-008 - <title>`.
6. Finalize per the finalization guide; `uv run pytest -q`.

Review items, one at a time: (a) layout and responsibilities above; (b) CLI and result-file shapes; (c) re-run vs copy for the backfill.

## Review (2026-10-08, @waylonflinn): items (a), (b), (c) approved as written

(b) settled shapes: CLI `td_score.py MODEL [--base-url] [--per-workflow N]`, `td_samples.py MODEL [--base-url]`, `jevbench.py MODEL [--base-url]`; `--base-url` default `https://saturn.wayforwardlabs.com`; `--per-workflow` below 100 writes no result file. Result files: `typed_decisions.json` = scratch shape + `ece` in every aggregate + `run` header {date, base_url, dataset_revision, scorer}; `samples.json` = scratch shape, one model per file, + `run` header; `jevbench.json` = jevbench `summary.json` verbatim + `run.json` under `run`. ECE: 10 equal-width bins on pmax, count-weighted |acc - mean pmax|; stated in the doc as this scorer's choice, not claimed equal to the board's.

(c) settled: backfill clef-flash-9b-Q8, winnow-12b-Q8, lev-4b-Q8 by re-running all three sets from the Mac through the router (about 25 min saturn time, one set at a time, check saturn is idle first). Record in doc-008 and the results README: doc-007's winnow JevBench row was from the manual 8099 server, the new row is through the router; jevbench latency columns include the tailscale hop.

7. Saturn cleanup (added at review). Only after step 4 reproduces the doc-007 figures within rounding and the results are committed: remove on saturn what the repo now holds or can recreate: `~/Build/results/jevbench-{8099,clef-flash-9b-Q8,lev-4b-Q8}/`, `~/Build/server8099.log`, `~/Build/start8099.sh` (its command line goes into doc-008 so it can be recreated), the `~/Build/jevbench` clone (the wrapper clones at c6004e0 on demand). Keep: `/opt/llama/models/*`, `models.ini` and its backups, `~/Build/llama.cpp`, `venv-gguf`, `gguf_add_decision.py`, `winnow_systemone.jinja`, `fork_prompt.py` (conversion tooling, NUMP-022 needs it; not this task's scope). If a figure does not reproduce, nothing is removed and the gap is reported. Deletion is confirmed with the user in-session before running.

Not started: waiting for the go-ahead to move to In Progress.

## Amendments during implementation (2026-10-08)
- Step 2: pyarrow is declared as PEP 723 inline metadata on td_score.py and td_samples.py (jevbench.py declares none), not as a dev dependency. Reason: with pyarrow in the venv, pandas uses Arrow strings and the policy sandbox blocks the call (5 test_policy failures).
- jevbench.py passes --price-in-per-m 0 --price-out-per-m 0, as the saturn runs did.
- samples.json shape: {model, run, cases: {case id: {q, t1_med, t5_med, tokens}}}.
- Step 7 approved in-session by @waylonflinn: commit, then remove the four saturn paths.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-08: scripts/eval/{harness,td_score,td_samples,jevbench}.py, results/<model>/ for clef-flash-9b-Q8, winnow-12b-Q8, lev-4b-Q8, tests/test_eval.py. Backfill re-run through the router from the Mac reproduces doc-007 exactly: td acc/KL/Brier/by-type acc and JevBench 190/198/170, Brier, ECE, ordinal MAE. Deviations from plan: (1) pyarrow is PEP 723 inline metadata on td_score/td_samples, not a dev dependency, because pyarrow in the venv makes pandas use Arrow strings and the policy sandbox blocks that (5 test_policy failures); follow-up chip offered. (2) samples.json shape is {model, run, cases:{id:...}}. (3) jevbench runs at price 0 (--price-in/out-per-m 0); default prices reported a fictitious charged_usd 4.62, so jevbench was re-run. doc-008 created; doc-005/doc-007 pointers; NUMP-021/022 --doc entries. uv run pytest: 274 passed.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-10-08 16:38
---
Plan ready for review
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Evaluation protocol is now repo infrastructure. scripts/eval/ has harness.py (pinned sets, systemone call, metrics, result files) and three commands run from the Mac against the saturn router with a model id: td_score.py (typed-decisions all/test, acc/KL/Brier/pmax/ECE), td_samples.py (distribution rows, t1/t5 warm medians), jevbench.py (clones jevbench c6004e0 on demand, runs typesafe adapter at price 0, stores public-export summary + manifest). Results live in scripts/eval/results/<model-id>/{typed_decisions,samples,jevbench}.json, a new model adds one directory. doc-008 states the protocol, saturn settings, tolerance (decision-002 item 4), results table, and the saturn-only list with recreation steps. Verified: re-running all three sets on clef-flash-9b-Q8, winnow-12b-Q8, lev-4b-Q8 reproduces every doc-007 figure exactly (td acc/KL/Brier/by-type acc, uniform KL 0.444 Brier 0.238, JevBench 190/198/170 with Brier, ECE, ordinal MAE); tests/test_eval.py checks metrics and stored results; uv run pytest 274 passed. Saturn copies (jevbench clone, results, server8099.log, start8099.sh) removed after commit. Follow-up offered: policy sandbox blocks pandas when pyarrow is installed.
<!-- SECTION:FINAL_SUMMARY:END -->
