---
id: doc-008
title: Decision model evaluation protocol
type: specification
created_date: '2026-10-08 19:26'
updated_date: '2026-10-09 15:37'
---
# Decision model evaluation protocol

This document states how numpty measures a local decision model (a model that serves `POST /v1/systemone`). NUMP-016, NUMP-016.01 and NUMP-018 used this procedure by hand. NUMP-021 put it in `scripts/eval/`. The next model needs three commands and adds one directory of results.

## Commands

Run each command from the repo root on the Mac. Each command sends requests to the saturn router, one at a time.

```bash
uv run scripts/eval/td_score.py MODEL
uv run scripts/eval/td_samples.py MODEL
uv run scripts/eval/jevbench.py MODEL
```

- `MODEL` is a router preset id, for example `winnow-12b-Q8`.
- `--base-url URL` changes the server. Default: `https://saturn.wayforwardlabs.com`.
- `td_score.py --per-workflow N` scores the first N cases of each workflow. Below 100 it prints the result and writes no file. Use it as a smoke test.
- Before a run, make sure that saturn is idle. Do not run two commands at the same time.
- Time on saturn per model: about 5 minutes for `td_score.py`, 1 minute for `td_samples.py`, 2 to 3 minutes for `jevbench.py`.

Each script declares its dependencies inline (PEP 723), so `uv run` gives it its own environment. The typed-decisions scripts need `pyarrow`. `jevbench.py` and jevbench itself use only the standard library. `pyarrow` is not a numpty dev dependency, because with `pyarrow` installed pandas uses Arrow strings and the numpty policy sandbox blocks that call (`tests/test_policy.py`). `jevbench.py` clones jevbench into `scripts/eval/data/jevbench/` on first use. `td_score.py` and `td_samples.py` download the dataset parquet into `scripts/eval/data/` on first use and check its sha256. `scripts/eval/data/` is gitignored.

## Fixed sets

| set | source | revision | items |
|---|---|---|---|
| JevBench public | `github.com/fstandhartinger/jevbench`, `datasets/public/{easy,original,hard}.jsonl`, in this order | c6004e008ffba24aec091261ca1a5c02f7324702 (the revision the Winnow author pins) | 231 items, one question each. Dataset hash `dc3995d8ae1e2fc8e81ce38431add509eb8bb39b85aadfd0c7c32079382dde51` |
| typed-decisions | `LocalLLaMA/typed-decisions`, config `all`, file `all/test-00000-of-00001.parquet` | d0e2f0c42fef86cc15d1688d25a19f5ba7c85b18 (2026-10-01). sha256 `4f294f218ea1da27f3efef936359389c62ea4d3973a41457732990f1d31b647c` | 400 cases, 100 per workflow, five questions per case, 2,000 decisions |

The four typed-decisions workflows are `agent_trace_observability`, `customer_service`, `invoice_processing` and `security_incidents`. The constants are in `scripts/eval/harness.py`. A change of revision is a change of protocol. Record it here and run all models again.

## Metrics and targets

JevBench (`jevbench.py`). The target is the one-hot label of each item. The jevbench `summarize --public-export` command computes every figure. The wrapper does not compute metrics.

- `n_correct` and `accuracy`: the top option equals the label.
- `macro_accuracy`: the mean of the per-family accuracies.
- `brier_mean`: Brier against the one-hot label.
- `ece`: expected calibration error, as jevbench computes it.
- `ordinal_mae`: mean absolute error on score items.
- `latency`: p50 and p95 seconds per request, as the client measures them.

typed-decisions (`td_score.py`). The target is the teacher distribution in `gold.probabilities`. The teacher is a 4B-class model, so these figures measure agreement with the teacher, not truth. All five questions of a case go in one request, as the board sends them.

- `acc`: the prediction equals `gold.label`. The prediction is `true` when the noul probability is 0.5 or more, the server's `choice` for a choice question, and the highest-probability level for a score question. The first key wins a tie.
- `kl`: KL(gold || model) in nats, with eps 1e-6. A key that the model does not return counts as 0.
- `brier`: the sum of squared differences over the union of the gold and model keys (multi-class Brier).
- `pmax`: the mean of the highest model probability. Compare it with `acc` to see sharpness.
- `ece`: 10 equal-width bins on `pmax`, the count-weighted mean of |accuracy - mean pmax| per bin. This is the choice of this scorer. It is not the same computation as the board ECE, so do not compare the two.
- `uniform_baseline`: the same metrics for a uniform distribution over the gold keys, which predicts the first gold key. It must be KL 0.444 and Brier 0.238, equal to the board's uniform row. Its accuracy is 0.269 against the board's 0.308, because the tie rule is different.

The result file has these aggregates for `all`, `uniform_baseline`, each question type (`by_type`) and each `workflow/question` (`per_question`).

## Throughput

- `td_score.py` records the wall time of each request from the Mac. The first request can load the model, so it is `cold_s`. `warm_p50_s` and `warm_max_s` use the other 399 requests. `tokens_mean` and `tokens_max` come from `usage.input_tokens`.
- `td_samples.py` measures warm latency on the first case of each workflow. It sends one unmeasured request, then takes the median of 5 requests with the first question only (`t1_med`). It then sends one unmeasured request and takes the median of 3 requests with all five questions (`t5_med`).
- All times include the tailscale hop from the Mac to saturn. A model that answers each question in its own prompt (lev, nimble) costs more per five-question case than a model that answers all questions in one prompt (clef). `t5_med` against `t1_med` shows this.
- The JevBench latency columns are the benchmark's own. Each request has one question, and the state repeats, so the prompt prefix is often in the cache.

## Distribution samples

`td_samples.py` writes one row per question of the first case of each workflow: the question type, the keys in display order (`false, true` for noul, the criteria keys for choice, `0..n-1` for score), the gold distribution, the model distribution and the gold label. Use these rows to see how sharp or flat a model is on the same questions as other models.

## Saturn settings

- Router: systemd unit `llama-server.service`, `/opt/llama/bin/llama-server --host 127.0.0.1 --port 4341 --sleep-idle-seconds 900 --cache-idle-slots --kv-unified --models-preset /opt/llama/config/models.ini --models-max 1 --models-autoload --tools all`. Build b11429 (llama.cpp main 2026-10-05).
- One model is in memory at a time. A request for another model unloads the current one. The server answers one request at a time, so all requests are sequential and the scripts do not retry.
- `models.ini` `[*]` defaults: `flash-attn = true`, `n-gpu-layers = 99`, `cache-type-k = q8_0`, `cache-type-v = q8_0`, `temp = 0.2`, `parallel = 1`, `load-mode = mlock`.
- Decision presets, Q8_0 weights except Quyet, all `jinja = true`:
  - `lev-4b-Q8`: `/opt/llama/models/lev-Q8_0.gguf`, `ctx-size = 32768`.
  - `clef-flash-9b-Q8`: `/opt/llama/models/Clef-Flash-Q8_0.gguf`, `mmproj = /opt/llama/models/mmproj-Clef-Flash-BF16.gguf`, `ctx-size`, `batch-size` and `ubatch-size` 16384.
  - `winnow-12b-Q8`: `/opt/llama/models/Winnow-12B-Q8_0-systemone.gguf` (converted per doc-007), `ctx-size = 8192`.
  - `quyet-large-Q4`: `/opt/llama/models/Quyet-1.0-Large.Q4_K_M-systemone.gguf` (Q4_K_M, converted per doc-009), `mmproj = /opt/llama/models/Quyet-1.0-Large.mmproj-f16.gguf`, `ctx-size = 32768`.
  - `gemma-4-31b-Q4-systemone`: `/opt/llama/models/gemma-4-31B-it-qat-UD-Q4_K_XL-systemone.gguf` (the chat preset's file plus the Quyet keys, doc-011), the `gemma-4-31b-Q4` lines (128k, q4_0 KV, MTP draft) plus `jinja = true`. `gemma-4-31b-Q4-systemone-32k`: the same file, `ctx-size = 32768`, `jinja = true`. Backup `models.ini.bak-2026-10-09`.
- Hardware: one RTX 3090, 24 GB.
- jevbench runs at price 0 (`--price-in-per-m 0 --price-out-per-m 0`), so `charged_usd` is 0. Without these flags jevbench uses its default prices and reports a cost that was not paid.

The board figures for hosted models use other quantizations and KV types. A comparison with the board is therefore a comparison across quantizations.

## Tolerance

From decision-002 item 4: a converted model passes when its rendered prompt text equals the source renderer and it reproduces the published benchmark figure within one item on JevBench public (or an agreed figure for another benchmark). A re-run of a model already in `results/` must give the same JevBench correct count within one item and the same typed-decisions accuracy, KL and Brier within rounding (0.0015). `tests/test_eval.py` checks the stored results of the three models in doc-007 against these limits.

## Results

Location: `scripts/eval/results/<model-id>/`, in the repo. Each model has three files:

- `typed_decisions.json`: the output of `td_score.py`. The `run` block has the date, base URL, dataset revision and scorer.
- `samples.json`: the output of `td_samples.py`, `{model, run, cases: {case id: {q, t1_med, t5_med, tokens}}}`.
- `jevbench.json`: the jevbench `summary.json` (public export) without changes, with the jevbench run manifest (`run.json`) under `run`.

A new model adds one directory. The scripts do not change. The raw jevbench run (predictions, ledger, raw responses) stays in `scripts/eval/data/runs/jevbench-<model>/`, which is not committed.

Stored results, measured 2026-10-08 through the router from the Mac. They equal the doc-005 and doc-007 figures on every accuracy, KL, Brier, ECE and JevBench count.

| model | JevBench correct / 231 | JevBench Brier | JevBench ECE | ordinal MAE | td accuracy | td KL | td Brier | td mean pmax | td ECE | td warm p50 | td mean input tokens | samples t1 / t5 (median) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| quyet-large-Q4 (Q4_K_M, measured 2026-10-08, NUMP-022) | 208 | 0.139 | 0.043 | 0.171 | 0.804 | 0.270 | 0.111 | 0.797 | 0.021 | 1.57 s | 1479 | 0.24 to 0.42 s / 0.93 to 1.82 s |
| gemma-4-31b-Q4-systemone (NUMP-026 test B: the chat preset's QAT Q4_K_XL file plus the Quyet openjev keys, no LoRA, chat preset settings; measured 2026-10-09, reference only) | 179 | 0.301 | 0.045 | 0.195 | 0.674 | 0.455 | 0.173 | 0.711 | 0.046 | 1.43 s | 1479 | 0.24 to 0.41 s / 0.82 to 1.66 s |
| gemma-4-31b-Q4-systemone-32k (same file, Quyet settings: 32k, q8_0 KV, no draft; JevBench only) | 180 | 0.294 | 0.047 | 0.200 | | | | | | | | |
| winnow-12b-Q8 | 198 | 0.205 | 0.067 | 0.189 | 0.702 | 0.629 | 0.238 | 0.858 | 0.156 | 0.79 s | 1721 | 0.28 s / 0.82 s |
| clef-flash-9b-Q8 | 190 | 0.235 | 0.058 | 0.243 | 0.707 | 0.209 | 0.110 | 0.703 | 0.010 | 0.34 s | 868 | 0.19 s / 0.30 s |
| lev-4b-Q8 | 170 | 0.397 | 0.119 | 0.420 | 0.637 | 0.297 | 0.165 | 0.639 | 0.043 | 0.58 s | 2464 | 0.25 s / 0.55 s |
| uniform (td only) | | | | | 0.269 | 0.444 | 0.238 | 0.318 | | | | |

"td" is typed-decisions. The two gemma-4-31b-Q4-systemone rows are the stock chat model with decision metadata (doc-011); they measure what the Quyet LoRA adds and are not recommended presets. The td ECE column is new in NUMP-021. The Quyet row is Q4_K_M weights (doc-009), the others Q8_0. Winnow is sharp and overconfident on the teacher labels (pmax 0.858 for accuracy 0.702). Clef-Flash is close to calibrated.

## What is not in the repo

These items are on saturn only.

- The router configuration: `/opt/llama/config/models.ini` with the decision presets above, and its backups `models.ini.bak-2026-10-06` and `.bak-2026-10-07`. To recreate a preset, copy the lines in "Saturn settings" into `models.ini`, then send `GET /v1/models?reload=1`.
- The GGUF files in `/opt/llama/models/`. lev and Clef-Flash come from `ggml-org`. To recreate the Winnow file, follow the conversion in doc-007. To recreate the Quyet file, follow doc-009 (the mradermacher Q4_K_M and mmproj plus the template in the doc).
- The conversion tools on saturn, tidied into `~/Build/numpty-eval/` on 2026-10-08 (NUMP-025 step 0): `convert/` (`gguf_add_decision.py`, `fork_prompt.py`, `winnow_systemone.jinja`, `quyet_systemone.jinja`, `models-ini-preset.txt`, `convert_and_start.sh`, `convert.log`), `probes/nump-022/` (the NUMP-022 probe scripts, request and answer JSON, `server8099*.log`), `venv/` (numpy, tqdm, pyyaml, pillow; use it with `PYTHONPATH=~/Build/llama.cpp/gguf-py`), `imagejev-preview/` (the NUMP-025 rebuilt set and runs). `~/Build/llama.cpp` stays where it is: it is the source of the `/opt/llama` binaries, not an evaluation artefact. Backup `models.ini.bak-2026-10-08`.

Removed from saturn after NUMP-021, because the repo holds or can recreate them:

- `~/Build/jevbench`. `jevbench.py` clones the pinned commit on demand.
- `~/Build/results/jevbench-{8099,clef-flash-9b-Q8,lev-4b-Q8}/`, if still present, and `~/Build/numpty-eval/probes/nump-022/server8099.log`. The summaries are in `scripts/eval/results/`.
- `~/Build/start8099.sh`, the manual verbose server for one GGUF. To recreate it, run this command on saturn. Stop it with `pkill -f "[p]ort 8099"`. Do not use `pkill llama-server`, because that stops the router.

```bash
nohup /opt/llama/bin/llama-server -m /opt/llama/models/Winnow-12B-Q8_0-systemone.gguf --host 127.0.0.1 --port 8099 -ngl 99 -fa on -c 8192 -ctk q8_0 -ctv q8_0 --parallel 1 --jinja --verbose --alias winnow-12b-Q8 > ~/Build/numpty-eval/probes/nump-022/server8099.log 2>&1 &
```

With `--verbose`, the server logs the rendered prompt of each task. To evaluate through it, run the commands on saturn with `--base-url http://127.0.0.1:8099`.

## History

- doc-007's Winnow JevBench row (198/231) was measured on the manual 8099 server. The stored `winnow-12b-Q8/jevbench.json` was measured through the router.
- doc-005 and doc-007 measured JevBench on saturn (`127.0.0.1`). The stored files were measured from the Mac, so their latency columns include the tailscale hop.
