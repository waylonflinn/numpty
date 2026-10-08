"""Shared parts of the decision-model evaluation: pinned sets, the systemone call, metrics, result files.

The protocol is in Backlog doc "Decision model evaluation protocol". Requests go to saturn one at a time.
"""

import datetime
import hashlib
import json
import math
import time
import urllib.request
from pathlib import Path

BASE_URL = "https://saturn.wayforwardlabs.com"
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RESULTS = HERE / "results"

DATASET_REPO = "LocalLLaMA/typed-decisions"
DATASET_REVISION = "d0e2f0c42fef86cc15d1688d25a19f5ba7c85b18"
DATASET_FILE = "all/test-00000-of-00001.parquet"
DATASET_SHA256 = "4f294f218ea1da27f3efef936359389c62ea4d3973a41457732990f1d31b647c"
WORKFLOWS = ("agent_trace_observability", "customer_service", "invoice_processing", "security_incidents")

JEVBENCH_REPO = "https://github.com/fstandhartinger/jevbench.git"
JEVBENCH_COMMIT = "c6004e008ffba24aec091261ca1a5c02f7324702"
JEVBENCH_FILES = ("easy", "original", "hard")


def systemone(model, state, questions, base_url=BASE_URL):
    """Sends one `POST /v1/systemone`. No retries.

    Returns:
        `(body, seconds)`: the parsed response and the wall time of the request.

    Raises:
        urllib.error.HTTPError: the server did not answer 200.
    """
    body = json.dumps({"model": model, "state": state, "questions": questions}).encode()
    request = urllib.request.Request(base_url + "/v1/systemone", data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
    start = time.time()
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.loads(response.read()), time.time() - start


def typed_decisions():
    """The pinned typed-decisions `all/test` cases, in file order.

    Downloads the parquet to `data/` on first use and checks its sha256.

    Returns:
        A list of dicts with `id`, `workflow`, and parsed `state`, `questions`, `gold`.
    """
    import pyarrow.parquet as pq
    path = DATA / "typed_decisions_test.parquet"
    if not path.exists():
        DATA.mkdir(exist_ok=True)
        url = f"https://huggingface.co/datasets/{DATASET_REPO}/resolve/{DATASET_REVISION}/{DATASET_FILE}"
        with urllib.request.urlopen(url, timeout=120) as response:
            path.write_bytes(response.read())
    if hashlib.sha256(path.read_bytes()).hexdigest() != DATASET_SHA256:
        raise ValueError(f"{path}: sha256 is not {DATASET_SHA256}; delete it to download again")
    return [{"id": row["id"], "workflow": row["workflow"], "state": json.loads(row["state"]),
             "questions": json.loads(row["questions"]), "gold": json.loads(row["gold"])}
            for row in pq.read_table(path).to_pylist()]


def probabilities(kind, answer):
    """The answer as `{key: p}`. A noul answer becomes `{"false": 1 - p, "true": p}`."""
    if kind == "noul":
        return {"false": 1 - answer["noul"], "true": answer["noul"]}
    return answer["probabilities"]


def argmax(p):
    """The key with the highest probability. The first key wins ties."""
    return max(p, key=p.get)


def kl(gold, model, eps=1e-6):
    """KL(gold || model) in nats. Keys missing from `model` count as 0."""
    return sum(g * math.log((g + eps) / (model.get(k, 0) + eps)) for k, g in gold.items() if g > 0)


def brier(p, gold):
    """Multi-class Brier: the sum of squared differences over the union of keys."""
    return sum((p.get(k, 0) - gold.get(k, 0)) ** 2 for k in set(p) | set(gold))


def ece(records, bins=10):
    """Expected calibration error of `records` (dicts with `acc` and `pmax`).

    10 equal-width bins on `pmax`, count-weighted |accuracy - mean pmax|. This scorer's choice; the JevBench
    board may bin differently.
    """
    binned = [[] for _ in range(bins)]
    for r in records:
        binned[min(int(r["pmax"] * bins), bins - 1)].append(r)
    return sum(len(b) * abs(sum(r["acc"] for r in b) - sum(r["pmax"] for r in b)) / len(b)
               for b in binned if b) / len(records)


def run_header(base_url, **extra):
    """The `run` block of a result file: date, base URL, and the given fields."""
    return {"date": datetime.date.today().isoformat(), "base_url": base_url, **extra}


def write_result(model, name, result):
    """Writes `results/<model>/<name>.json`. Returns the path."""
    path = RESULTS / model / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=1) + "\n")
    return path
