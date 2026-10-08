# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Runs JevBench public (231 items) on one decision model and stores the summary.

Usage: uv run scripts/eval/jevbench.py MODEL [--base-url URL]

Clones jevbench at the pinned commit into `data/jevbench/` on first use. Runs the `typesafe` adapter without auth
and at price 0, sequential, no retries; the raw run goes to `data/runs/jevbench-MODEL/`. Writes `results/MODEL/jevbench.json`:
the `summarize --public-export` output with the run manifest under `run`.
"""

import argparse
import json
import subprocess
import sys

from harness import BASE_URL, DATA, JEVBENCH_COMMIT, JEVBENCH_FILES, JEVBENCH_REPO, write_result


def checkout():
    """The jevbench clone at `JEVBENCH_COMMIT`, cloned on first use."""
    path = DATA / "jevbench"
    if not path.exists():
        subprocess.run(["git", "clone", "--quiet", JEVBENCH_REPO, str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "checkout", "--quiet", JEVBENCH_COMMIT], check=True)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("model")
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()

    repo = checkout()
    run = DATA / "runs" / f"jevbench-{args.model}"
    if run.exists():
        sys.exit(f"{run} exists; remove it to run again")
    run.mkdir(parents=True)
    tasks = ",".join(str(repo / "datasets" / "public" / f"{name}.jsonl") for name in JEVBENCH_FILES)
    cli = [sys.executable, "-m", "jevbench.cli"]
    files = {"--results": run / "predictions.jsonl", "--ledger": run / "ledger.jsonl"}
    paths = [str(x) for kv in files.items() for x in kv]
    subprocess.run(cli + ["run", "--tasks", tasks, "--adapter", "typesafe", "--endpoint", args.base_url,
                          "--model", args.model, "--key-env", "", "--price-in-per-m", "0", "--price-out-per-m", "0",
                          "--raw-dir", str(run / "raw"),
                          "--run-label", args.model, "--manifest", str(run / "run.json"), *paths],
                   cwd=repo, check=True)
    subprocess.run(cli + ["summarize", "--tasks", tasks, "--public-export", str(run / "summary.json"), *paths],
                   cwd=repo, check=True, stdout=subprocess.DEVNULL)
    result = json.loads((run / "summary.json").read_text())
    result["run"] = json.loads((run / "run.json").read_text())
    print({k: result.get(k) for k in ("accuracy", "n_correct", "brier_mean", "ece")})
    print(write_result(args.model, "jevbench", result))


if __name__ == "__main__":
    main()
