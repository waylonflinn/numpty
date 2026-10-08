# /// script
# requires-python = ">=3.12"
# dependencies = ["pyarrow"]
# ///
"""Records sample distributions and warm latency of one decision model on typed-decisions.

Usage: uv run scripts/eval/td_samples.py MODEL [--base-url URL]

Uses the first test case of each workflow. Per case: the model and gold distribution of every question, and the
warm median latency for the first question alone (5 repeats) and for all questions (3 repeats). Writes
`results/MODEL/samples.json`.
"""

import argparse
import statistics

from harness import BASE_URL, DATASET_REVISION, WORKFLOWS, probabilities, run_header, systemone, typed_decisions, \
    write_result


def keys(question):
    """The answer keys of a question in display order: `false, true`, choice keys, or score levels `0..n-1`."""
    if question["type"] == "noul":
        return ["false", "true"]
    if question["type"] == "choice":
        return list(question["criteria"])
    return [str(i) for i in range(len(question["criteria"]))]


def warm_median(model, state, questions, base_url, repeats):
    """Median seconds of `repeats` requests after one unmeasured request."""
    systemone(model, state, questions, base_url)
    return statistics.median(systemone(model, state, questions, base_url)[1] for _ in range(repeats))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("model")
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()

    rows = typed_decisions()
    cases = {}
    for wf in WORKFLOWS:
        case = next(r for r in rows if r["workflow"] == wf)
        state, qs, gold = case["state"], case["questions"], case["gold"]
        body, _ = systemone(args.model, state, qs, args.base_url)
        per_q = {}
        for name, q in qs.items():
            p = probabilities(q["type"], body["answers"][name])
            ks = keys(q)
            per_q[name] = {"type": q["type"], "keys": ks, "gold": [gold[name]["probabilities"][k] for k in ks],
                           "model": [p[k] for k in ks], "gold_label": gold[name]["label"]}
        first = dict(list(qs.items())[:1])
        cases[case["id"]] = {"q": per_q, "t1_med": warm_median(args.model, state, first, args.base_url, 5),
                             "t5_med": warm_median(args.model, state, qs, args.base_url, 3),
                             "tokens": body["usage"]["input_tokens"]}
        print(case["id"], "t1 %.3f t5 %.3f tokens %d" % (cases[case["id"]]["t1_med"], cases[case["id"]]["t5_med"],
                                                         cases[case["id"]]["tokens"]), flush=True)
    result = {"model": args.model, "run": run_header(args.base_url, dataset_revision=DATASET_REVISION),
              "cases": cases}
    print(write_result(args.model, "samples", result))


if __name__ == "__main__":
    main()
