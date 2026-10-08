"""Offline tests of the evaluation metrics and the stored per-model results in scripts/eval/results."""

import json

import pytest

from harness import RESULTS, argmax, brier, ece, kl
from td_score import uniform

# doc-007: typed-decisions all/test (acc, KL, Brier, noul acc, choice acc, score acc) and JevBench public correct/231
RECORDED = {"clef-flash-9b-Q8": ((0.707, 0.209, 0.110, 0.818, 0.710, 0.620), 190),
            "winnow-12b-Q8": ((0.702, 0.629, 0.238, 0.788, 0.657, 0.671), 198),
            "lev-4b-Q8": ((0.637, 0.297, 0.165, 0.757, 0.617, 0.562), 170)}
ROUNDING = 0.0015


def stored(name):
    return {p.parent.name: json.loads(p.read_text()) for p in sorted(RESULTS.glob(f"*/{name}.json"))}


def test_kl_of_equal_distributions_is_zero():
    assert kl({"a": 0.3, "b": 0.7}, {"a": 0.3, "b": 0.7}) == pytest.approx(0)


def test_kl_counts_missing_model_keys_as_zero():
    assert kl({"a": 1.0}, {"b": 1.0}) == pytest.approx(13.8155, abs=1e-3)


def test_brier_of_one_hot_miss_is_two():
    assert brier({"a": 1.0}, {"b": 1.0}) == 2


def test_argmax_tie_takes_first_key():
    assert argmax({"x": 0.5, "y": 0.5}) == "x"


def test_ece_of_calibrated_bin_is_zero():
    assert ece([{"acc": 1.0, "pmax": 0.75}] * 3 + [{"acc": 0.0, "pmax": 0.75}]) == pytest.approx(0)


def test_ece_weights_bins_by_count():
    records = [{"acc": 1.0, "pmax": 0.95}] * 3 + [{"acc": 1.0, "pmax": 0.55}]
    assert ece(records) == pytest.approx((3 * 0.05 + 0.45) / 4)


def test_uniform_predicts_first_gold_key():
    record = uniform({"label": "b", "probabilities": {"a": 0.2, "b": 0.8}})
    assert record["acc"] == 0 and record["pmax"] == 0.5 and record["brier"] == pytest.approx(0.18)


@pytest.mark.parametrize("model,result", stored("typed_decisions").items())
def test_stored_uniform_baseline(model, result):
    assert result["decisions"] == 2000
    assert (result["uniform_baseline"]["kl"], result["uniform_baseline"]["brier"]) == (0.444, 0.238)


@pytest.mark.parametrize("model", RECORDED)
def test_typed_decisions_reproduce_doc_007(model):
    result = stored("typed_decisions")[model]
    got = (result["all"]["acc"], result["all"]["kl"], result["all"]["brier"],
           *(result["by_type"][k]["acc"] for k in ("noul", "choice", "score")))
    assert got == pytest.approx(RECORDED[model][0], abs=ROUNDING)


@pytest.mark.parametrize("model", RECORDED)
def test_jevbench_reproduces_doc_007(model):
    assert abs(stored("jevbench")[model]["n_correct"] - RECORDED[model][1]) <= 1
