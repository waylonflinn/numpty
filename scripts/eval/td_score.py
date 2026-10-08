# /// script
# requires-python = ">=3.12"
# dependencies = ["pyarrow"]
# ///
"""Scores one decision model on typed-decisions `all/test` against the teacher distributions.

Usage: uv run scripts/eval/td_score.py MODEL [--base-url URL] [--per-workflow N]

One request per case, sequential. Writes `results/MODEL/typed_decisions.json` only for the full set
(100 cases per workflow, 2,000 decisions); a smaller `--per-workflow` prints the result and writes nothing.
"""

import argparse
import json
import statistics

from harness import BASE_URL, DATASET_REVISION, WORKFLOWS, argmax, brier, ece, kl, probabilities, run_header, \
    systemone, typed_decisions, write_result

FULL = 100


def score(kind, answer, gold):
    """One decision record: `acc`, `kl`, `brier`, `pmax` of the answer against the gold entry."""
    p = probabilities(kind, answer)
    if kind == "noul":
        pred = "true" if answer["noul"] >= 0.5 else "false"
    elif kind == "choice":
        pred = answer["choice"]
    else:
        pred = argmax(p)
    g = gold["probabilities"]
    return {"acc": float(pred == gold["label"]), "kl": kl(g, p), "brier": brier(p, g), "pmax": max(p.values())}


def uniform(gold):
    """The uniform-distribution record for a gold entry. Its prediction is the first gold key."""
    g = gold["probabilities"]
    u = {k: 1 / len(g) for k in g}
    return {"acc": float(gold["label"] == next(iter(g))), "kl": kl(g, u), "brier": brier(u, g), "pmax": 1 / len(g)}


def aggregate(records):
    """Mean of each metric over `records`, plus `n` and `ece`, rounded to 3 places."""
    out = {"n": len(records)}
    for key in ("acc", "kl", "brier", "pmax"):
        out[key] = round(sum(r[key] for r in records) / len(records), 3)
    out["ece"] = round(ece(records), 3)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("model")
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--per-workflow", type=int, default=FULL)
    args = parser.parse_args()

    rows = typed_decisions()
    cases = [c for wf in WORKFLOWS for c in [r for r in rows if r["workflow"] == wf][:args.per_workflow]]
    by_type, per_question, baseline, seconds, tokens = {"noul": [], "choice": [], "score": []}, {}, [], [], []
    for i, case in enumerate(cases):
        body, dt = systemone(args.model, case["state"], case["questions"], args.base_url)
        seconds.append(dt)
        tokens.append(body["usage"]["input_tokens"])
        for name, gold in case["gold"].items():
            record = score(gold["type"], body["answers"][name], gold)
            by_type[gold["type"]].append(record)
            per_question.setdefault(f'{case["workflow"]}/{name}', []).append(record)
            baseline.append(uniform(gold))
        if (i + 1) % 50 == 0:
            print(f"{i + 1}/{len(cases)}", flush=True)

    warm = seconds[1:]  # the first request may load the model
    records = [r for rs in by_type.values() for r in rs]
    result = {"model": args.model,
              "run": run_header(args.base_url, dataset_revision=DATASET_REVISION, scorer="scripts/eval/td_score.py"),
              "cases": len(cases), "decisions": len(records), "cold_s": round(seconds[0], 2),
              "warm_p50_s": round(statistics.median(warm), 3), "warm_max_s": round(max(warm), 3),
              "tokens_mean": round(sum(tokens) / len(tokens)), "tokens_max": max(tokens),
              "all": aggregate(records), "uniform_baseline": aggregate(baseline),
              "by_type": {k: aggregate(v) for k, v in by_type.items()},
              "per_question": {k: aggregate(v) for k, v in per_question.items()}}
    print(json.dumps({k: result[k] for k in ("cases", "decisions", "warm_p50_s", "all", "uniform_baseline",
                                             "by_type")}, indent=1))
    if args.per_workflow >= FULL:
        print(write_result(args.model, "typed_decisions", result))


if __name__ == "__main__":
    main()
