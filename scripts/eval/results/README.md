# Decision model results

One directory per router model id. Each has `typed_decisions.json` (`td_score.py`), `samples.json` (`td_samples.py`) and `jevbench.json` (`jevbench.py`). Backlog doc-008 "Decision model evaluation protocol" states the method and the file shapes.

- The `winnow-12b-Q8` JevBench row in doc-007 came from the manual server on port 8099. The file here came through the router.
- These JevBench runs went from the Mac to saturn. Their latency columns include the tailscale hop. The doc-005 and doc-007 runs went from saturn itself.
