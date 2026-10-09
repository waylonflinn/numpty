---
id: doc-009
title: Quyet-1.0-Large to a llama.cpp decision GGUF (NUMP-022)
type: specification
created_date: '2026-10-08 20:44'
updated_date: '2026-10-08 23:23'
tags:
  - research
  - decision-models
  - nump-022
---
Research spike NUMP-022, 2026-10-08. Question: can Quyet-1.0-Large, first on JevBench v1.6.1, be served by upstream llama-server through the metadata-only conversion of doc-007, and does it change the requirement-to-model table of decision-002. Decision: decision-003. Evaluation protocol and stored results: doc-008 (`scripts/eval/results/quyet-large-Q4/`).

## Summary

- Quyet-1.0-Large needs no fork. A copy of the published `mradermacher` Q4_K_M GGUF with five added header keys (`gemma4.decision.type = openjev`, three per-type temperature keys, one `systemone` template) is served by upstream llama-server b11429 on saturn at 32k context with q8_0 KV: 21.0 GB VRAM, 22.3 GB with the Gemma 4 mmproj. Tensors untouched.
- The upstream server renders the quyet package's prompt (version 2) byte for byte and tokenizes it to the same count. On the 231-item JevBench public subset it scores 208/231 (0.900), Brier 0.139, ECE 0.043: 10 items ahead of Winnow (198), 18 ahead of Clef-Flash (190). The figure of 0.909 named in the task (210/231) is two items higher, one outside the tolerance; its source could not be found anywhere today (see AC #4), and a Q4_K_M against a bf16 run is the plain explanation.
- typed-decisions (2,000 decisions): accuracy 0.804 against 0.707 (Clef-Flash), 0.702 (Winnow) and 0.727 (Jev 1.13, board). KL 0.270 and Brier 0.111 against the teacher, mean p_max 0.797 for 0.804 accuracy: close to Clef-Flash's calibration (0.209, 0.110), far from Winnow's (0.629, 0.238).
- Throughput is the cost. One prompt per question on a 31B model: warm p50 1.57 s for a five-question case (Winnow 0.79 s, Clef-Flash 0.34 s), JevBench p95 2.4 s on long states.
- Images work mechanically and, on a synthetic probe, correctly: with the mmproj a red circle gets red 0.98, circle 0.97, text 0.08, the same answers as Clef-Flash; the text-only control is near uniform. Quyet never trained with images, so this is one probe, not a measurement of image accuracy.
- `numpty.TypeSafe` answers Choice, Score and Noul through the router preset `quyet-large-Q4`: cold 4.6 s, warm 0.3 s.
- Decision (decision-003): Quyet takes the text-accuracy row from Winnow and the image and calibration rows from Clef-Flash. Clef-Flash stays for throughput and for the 10 GB of VRAM that Quyet does not leave.

## Quyet's decision mechanism (AC #1)

Sources: `github.com/ncchinh/quyet` at d2514fe (2026-10-08, package version 1.0.2): `src/quyet/llm/prompt.py`, `src/quyet/llm/runtime.py`, `src/quyet/questions.py`, `src/quyet/calibration.py`, `src/quyet/answers.py`, `tests/test_llm.py`. Model repo `huggingface.co/chinhnc/Quyet-1.0-Large` at 3a3c5e7d (2026-10-08): `quyet_config.json`, `chat_template.jinja`, `tokenizer.json`, README. doc-005 read the same files on 2026-10-05; the repository has two commits (2026-10-04 and 2026-10-08) and the prompt code did not change between them. The 2026-10-08 commits add the quyet.ai demo link and the `encoder/` runtime for the Small and Tiny models, which this task does not use.

Mechanism (`runtime.py` `LLMModel`, `prompt.py`):

- One forward pass per question. The runtime reads the logits of the letter tokens at the last prompt token (`logits_to_keep=1`). Nothing is generated.
- Labels: `A`..`J`, one letter per option, in option order. `letter_ids()` requires each letter to be one token. `MAX_OPTIONS = 10`; an eleventh option is rejected with `QuestionError`, not truncated.
- Probabilities: `softmax(logits / T)` over the first k letters. `T` comes from `quyet_config.json` `temperatures`, keyed by question type: choice 1.3007, score 1.3159, noul 1.4957. `calibration.temperature()` looks for `<type>:<bucket>` first and then `<type>`; the LLM config has type keys only, so the option count does not change the temperature.
- noul: option A is the `true` description, option B the `false` description. The answer is `p(A)`. The fallback texts are the literal `true` and `false`.
- choice: options in the order of the `criteria` object (or list). The answer is the key with the highest probability.
- score: levels in order, keys `0`..`K-1`. The answer is `sum(i * p_i)`.
- confidence: `p_max` for choice and score, `max(p, 1 - p)` for noul. This is not the TypeSafe formula.
- Option text (`questions.describe()` and `prompt.option_texts()`): a string is used as it is. A falsy value (`null`, `""`, `0`, `false`, `{}`, `[]`) means no description: the choice key, the level index, or `true`/`false`. Any other JSON value is `json.dumps(value, ensure_ascii=False, separators=(", ", ": "))`.
- State: a string is used as it is. A JSON object or list is `json.dumps(state, ensure_ascii=False, separators=(",", ":"))` (prompt version 2; version 1 used `indent=1`).
- Truncation: the state is cut to 6,000 tokens (a list keeps its tail with a leading `… `, anything else keeps its head with a trailing ` …`) and the whole prompt to 8,000 tokens (`max_prompt_tokens`), shrinking the state budget until the longest question fits. Below 256 state tokens the request is rejected.

Prompt version 2 (`quyet_config.json` `prompt_version: 2`): one user turn, no system message, no closing line, rendered by the Gemma 4 chat template with `add_generation_prompt=True` and `enable_thinking=False`, then tokenized as one string with `add_special_tokens=False` (the template emits `<bos>` itself).

```
<bos><|turn>user
State:
{state text}

Question: {instructions}
{one of:
 "Choose the option that fits best." |
 "Choose the level that fits best (levels are ordered from lowest to highest)." |
 "Choose A if the statement is true for this state, B if it is not."}

Options:
A. {option text 0}
B. {option text 1}
...<turn|>
<|turn>model
<|channel>thought
<channel|>
```

The chat template trims the user content, so trailing whitespace of the last option text is removed. The prompt ends with `<channel|>` and no newline. The model card confirms the version 2 description ("the trained prompt without the system message and the closing line, with structured states as compact JSON (about 68 fewer input tokens per decision); its temperatures were refit for it").

### Match with upstream `openjev`

Source: `tools/server/server-decision.cpp` at b11429 on saturn (`~/Build/llama.cpp`), same build as doc-007.

| item | Quyet | upstream `openjev` | match |
|---|---|---|---|
| readout | letter logits at the last prompt token, one prompt per question | same, labels assigned from `labels` to the first k options | yes |
| labels | `A`..`J`, each one token | `A`-`Z` then `a`-`z`, each must be one token, max 52 | yes for 1 to 10 options. All 52 letters are single tokens in the Gemma 4 vocabulary (checked on the base GGUF), so the model loads. Options 11 to 52 render as `K`..`Z`, `a`..`z` in prompts Quyet never saw. The server does not enforce 10; the client must. |
| noul order | A = true, B = false | the server swaps to true first; the template cannot change it | yes |
| temperature | per type, `softmax(logit / T)` | `gemma4.decision.temperature.<type>.<bucket>` then `.<type>`, `exp((s - max) / T)` normalized | yes; the buckets (`2`, `3_5`, `6_10`, `11`) are not needed |
| option-order averaging | none | none for openjev (one variant) | yes |
| `confidence` | `p_max` | TypeSafe formulas: choice `(p_max - 1/n) / (1 - 1/n)`, score from the distance to the mode, noul derived by numpty | differs by design, as for Winnow. A client can recompute `p_max` from `probabilities`. |
| `score` answer | `sum(i * p_i)` | same | yes |
| images | none; no image path in the runtime | passed to mtmd when the server has an mmproj | mechanically possible, untested by the author (AC #6) |
| key order | request order (`json.loads`) | request order (`nlohmann::ordered_json`, `common_json`) | yes |
| truncation | 6,000 state tokens, 8,000 prompt tokens | none; a prompt longer than the context is an error | the server accepts prompts Quyet never trained on; the preset context (32k) is the only cap |
| choice criteria as a list | accepted (labels without descriptions) | rejected, `criteria` must be an object (400) | client-side difference |
| `instructions` | non-empty string required | any JSON value, rendered by the template | client-side difference |
| option limit | 2 to 10 | 2 to 52 (score 2 to 10) | see labels |

Verdict: type `openjev` is the match. The two formula differences (`confidence`) and the two limits (10 options, 8,000-token prompt) are client-side caveats, the same class as for Winnow.

## Conversion (AC #2)

Files on saturn, `/opt/llama/models/`:

| file | source | sha256 | size |
|---|---|---|---|
| `Quyet-1.0-Large.Q4_K_M.gguf` | `mradermacher/Quyet-1.0-Large-GGUF` at 112e27ad (2026-10-05), static quant, `general.file_type` 15 | `e7fc4952…67be` (equals the HF LFS hash) | 18.69 GB |
| `Quyet-1.0-Large.mmproj-f16.gguf` | same repo | `299ed79f…9228` | 1.20 GB |
| `Quyet-1.0-Large.Q4_K_M-systemone.gguf` | copy of the first with five added header keys (64 keys, 833 tensors, tensors unchanged) | | 18.69 GB |

Quant and context (review decision 2026-10-08): Q4_K_M, context 32,768 with the saturn default q8_0 KV and flash attention. Measured on the manual server (`llama-server --verbose`, port 8099, same flags as the preset): weights 17.8 GB, KV 1.36 GB for the 10 global layers at 32,768 cells plus 0.64 GB for the 50 sliding-window layers at 1,536 cells, compute 0.4 GB.

| configuration | VRAM (`nvidia-smi`) |
|---|---|
| ctx 8192, no mmproj | 19.8 GB |
| ctx 32768, no mmproj | 21.0 GB |
| ctx 32768, mmproj f16, after an image request | 22.3 GB |

doc-006 estimated 22 GB at 8k with f16 KV because it averaged `head_count_kv` over all layers. Gemma 4 31B has 4 KV heads on the 10 global layers and 16 on the 50 sliding layers, and llama.cpp keeps only 1,536 cells for the sliding layers, so the KV cache is 2 GB at 32k with q8_0 and the 32k target fits with the q8_0 KV. No fallback to 16k or q4_0 KV was needed.

Keys added with `gguf_add_decision.py` (doc-007, unchanged, run on saturn with the gguf venv, now `~/Build/numpty-eval/venv`; the 18.7 GB copy took 10 s):

| key | type | value |
|---|---|---|
| `gemma4.decision.type` | string | `openjev` |
| `gemma4.decision.temperature.choice` | float32 | 1.3007 |
| `gemma4.decision.temperature.score` | float32 | 1.3159 |
| `gemma4.decision.temperature.noul` | float32 | 1.4957 |
| `tokenizer.chat_template.systemone` | string | the template below |

```bash
cd ~/Build/numpty-eval/convert && PYTHONPATH=$HOME/Build/llama.cpp/gguf-py ../venv/bin/python gguf_add_decision.py \
  /opt/llama/models/Quyet-1.0-Large.Q4_K_M.gguf /opt/llama/models/Quyet-1.0-Large.Q4_K_M-systemone.gguf \
  --type openjev --template $HOME/Build/numpty-eval/convert/quyet_systemone.jinja \
  --temperature choice=1.3007 --temperature score=1.3159 --temperature noul=1.4957
```

Template `quyet_systemone.jinja` (`~/Build/numpty-eval/convert/` on saturn; the paths in the command above are the ones after the 2026-10-08 tidy, NUMP-025 step 0):

```jinja
{#- Quyet-1.0-Large systemone template (llama.cpp decision type openjev).
    Reproduces quyet src/quyet/llm/prompt.py build_prompt() with prompt_version 2: one user turn, no system
    message, no closing line, a string state as it is, any other state as compact JSON, options lettered
    "A. text" with the trained fallbacks (key for choice, level index for score, "true"/"false" for noul),
    rendered by the Gemma 4 chat template with thinking off. The server puts the true option first for noul.
    Images: Quyet has no image path; the markers are placed before the state so that a request with images
    is mechanically possible. llama.cpp's jinja strips one trailing newline, so the file ends with one. -#}
{%- set letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz" -%}
{%- if type == "choice" -%}
{%- set kind = "Choose the option that fits best." -%}
{%- elif type == "score" -%}
{%- set kind = "Choose the level that fits best (levels are ordered from lowest to highest)." -%}
{%- else -%}
{%- set kind = "Choose A if the statement is true for this state, B if it is not." -%}
{%- endif -%}
{%- if state is string -%}
{%- set state_text = state -%}
{%- else -%}
{%- set state_text = state | tojson(separators=[",", ":"]) -%}
{%- endif -%}
{%- set ns = namespace(opts="") -%}
{%- for o in options -%}
{%- if not o.description -%}
{%- set t = o.key -%}
{%- elif o.description is string -%}
{%- set t = o.description -%}
{%- else -%}
{%- set t = o.description | tojson -%}
{%- endif -%}
{%- set ns.opts = ns.opts ~ letters[loop.index0] ~ ". " ~ t ~ ("\n" if not loop.last else "") -%}
{%- endfor -%}
{%- set user = "State:\n" ~ state_text ~ "\n\nQuestion: " ~ instructions ~ "\n" ~ kind ~ "\n\nOptions:\n" ~ ns.opts -%}
<bos><|turn>user
{% for img in images %}{{ img }}
{% endfor %}{{ user | trim }}<turn|>
<|turn>model
<|channel>thought
<channel|>
```

Notes on the template:

- `<bos>` is literal text, as in doc-007. Upstream tokenizes the rendered prompt with `parse_special` and no automatic BOS; Quyet's `add_special_tokens=False` relies on the `<bos>` the chat template emits. Same token.
- The state uses `tojson(separators=[",", ":"])`; non-string option descriptions use `tojson` with the engine's default separators `, ` and `: `, which equal Python's defaults. Neither escapes `<` (Quyet does not). Non-ASCII stays UTF-8 on both sides. Floats: the engine prints six significant digits, Python the shortest round trip; the fixed sets have no long floats.
- `not o.description` reproduces `describe()`'s falsy rule; the empty-string description in the sample rendered as the key, as in Quyet.
- `letters[loop.index0]` indexes a string; the engine supports it. The 52 letters match the server's label order, so a prompt with more than 10 options renders the letters the server reads.
- `user | trim` reproduces the chat template's `message['content'] | trim`.
- The file ends with one newline, which the engine strips: the prompt ends with `<channel|>`.
- The `images` loop puts one media marker per image before `State:`. With no images it renders nothing, so text prompts are unchanged.

Verification of the prompt text. `quyet_prompt.py` (scratch) renders requests with the quyet package's own `build_prompt()` and `truncate_state()` and the model repo's tokenizer (`transformers.AutoTokenizer`, `chat_template.jinja`). `compare_prompts.py` (scratch) sends the same requests to the verbose server and reads the `"prompt"` field that `launch_slot_` logs. Sample `requests.json`: the README example (choice with a `null` description, noul without criteria, score), a string state with `<`, `&`, quotes and a newline with a noul with both descriptions and a score with a `null` level and a JSON level, a conversation-list state with non-ASCII and a choice with a JSON description, an empty-string description and a quote-and-backslash description, and a 10-option choice on a JSON state with a float, booleans and `null`. Result: all 7 rendered prompts equal the replica, in two runs, and the server's `usage.input_tokens` equals the replica's token count for every request (203, 184, 87, 91). Unlike Winnow there is no tokenizer boundary difference, because Quyet tokenizes the prompt as one string too. The server log is block-buffered when redirected to a file, so prompts appear a few requests late; the comparison reads the whole sequence.

Server answers on the README example (same values through the router and `numpty.TypeSafe`): intent `cancel` 0.9966, urgent `p(true)` 0.721, mood `score` 0.24 on `calm / annoyed / angry` (0.770, 0.219, 0.011). The quyet.ai demo shows `cancel` as the top answer for a longer version of the same message; the author publishes no probabilities for this exact request, so the first-order check of the conversion is the benchmark below.

## Result on saturn (AC #3)

Preset `quyet-large-Q4` in `/opt/llama/config/models.ini` (backup `models.ini.bak-2026-10-08`): the converted GGUF, `mmproj = Quyet-1.0-Large.mmproj-f16.gguf`, `ctx-size = 32768`, `jinja = true`, the `[*]` defaults (`-ngl 99`, flash attention, q8_0 KV, `parallel = 1`). Loaded with `GET /v1/models?reload=1`.

- `GET /v1/models` reports `output_modalities: ["decisions"]` and `input_modalities: ["text", "image"]` for `quyet-large-Q4` (Clef-Flash reports `["text", "image", "video"]`, Winnow `["text"]`).
- `numpty.TypeSafe("quyet-large-Q4", base_url="https://saturn.wayforwardlabs.com", api_key="x")` answered the README example: `intent` cancel 0.9966 (confidence 0.9949), `urgent` True 0.721, `mood` 0.24 on three levels. Cold 4.6 s (load from the page cache, 17.8 GB to the GPU), warm 0.27 to 0.31 s from the Mac over tailscale.
- Loading Quyet on the router unloads the resident model (`--models-max 1`), as for every preset. Quyet and Clef-Flash (13.8 GB) or Winnow (13.1 GB) cannot be co-resident on the 3090.

## Comparison with the published figure (AC #4)

Method: doc-008 protocol, `uv run scripts/eval/jevbench.py quyet-large-Q4` from the Mac through the router, jevbench c6004e0, `typesafe` adapter, the three public files (231 items), sequential, no retries. Result `scripts/eval/results/quyet-large-Q4/jevbench.json`.

| | upstream llama-server, converted Q4_K_M GGUF, RTX 3090, q8_0 KV, 32k |
|---|---|
| correct / 231 | 208 (90.04%) |
| macro accuracy | 0.911 |
| Brier | 0.139 |
| ECE | 0.043 |
| ordinal MAE | 0.171 |
| schema validity | 1.0 |
| paraphrase agreement | 35 of 36 pairs |
| p50 / p95 latency (from the Mac) | 0.27 s / 2.40 s |

Per family (correct rate): adequacy, adversarial, extraction, fact, intent, ordinal, probability, routing, routing_hard, tool_selection and trap 1.00; judge_hard 0.94; policy 0.92; ambiguous 0.86; multi_hop and tradeoff 0.83; long_policy 0.68 (Winnow 0.79, the one family where Winnow is ahead); temporal_numeric 0.33 (Winnow 0.33). The 23 misses are concentrated in long_policy (6 of 19) and temporal_numeric (4 of 6).

The published figure. The task and doc-005 name "public-test accuracy 0.909, hard ECE 0.089". Searched on 2026-10-08 without finding it: the Benchmark Heaven board page and API JSON for v1.6.0 and v1.6.1 (the Quyet record has 300 open items, not 231, and reports Intelligence 73.4, Calibration 90.0, per-type accuracies choice 0.871, noul 0.848, score 0.749 on 1,500 items, noul ECE 0.046, choice hard ECE 0.053, score top ECE 0.075; no value near 0.909 or 0.089), the model card at its four revisions, quyet.ai, the quyet repository's two commits, and the jevbench repository at c6004e0 and at HEAD. The nearest values on the board are the noul calibration score 90.7 and the noul decisive rate 0.912. So there is no author figure on the 231-item set to reproduce, and 0.909 (210/231) is treated as the task's reference. Gap: 2 items, one outside the decision-002 tolerance.

What was tried and ruled out for the gap: the rendered prompt equals the author's renderer on 7 varied questions, so the prompt is not the cause; the token counts equal, so tokenization is not the cause; the temperatures are the config values and the server looks them up by type (`get_temperature()` falls back from `<type>.<bucket>` to `<type>`); the labels A..J are the server's first ten; noul order is true first on both sides. What remains is the quantization: the board measured bf16 on an H100 and this run is Q4_K_M, the same mismatch doc-006 notes for every 27B and 31B row. A Q8_0 (32.7 GB) does not fit the 3090 and Q5_K_M (21.9 GB) leaves 2 GB for everything else, so the quant was not changed (review decision). The gap is reported, not closed.

The same 231 items on the other saturn decision models (doc-008 stored results, same scorer, same day for Quyet, 2026-10-08 for the rest):

| model (saturn, router, q8_0 KV) | correct / 231 | accuracy | macro accuracy | Brier | ECE | ordinal MAE | p50 / p95 (from the Mac) |
|---|---|---|---|---|---|---|---|
| **quyet-large-Q4** | **208** | **0.900** | **0.911** | **0.139** | **0.043** | **0.171** | 0.27 s / 2.40 s |
| winnow-12b-Q8 | 198 | 0.857 | 0.855 | 0.205 | 0.067 | 0.189 | 0.25 s / 1.14 s |
| clef-flash-9b-Q8 | 190 | 0.823 | 0.827 | 0.235 | 0.058 | 0.243 | **0.22 s / 0.86 s** |
| lev-4b-Q8 | 170 | 0.736 | 0.744 | 0.397 | 0.119 | 0.420 | 0.23 s / 1.04 s |

Quyet leads every quality column, including ECE, where Clef-Flash led before.

## Protocol rows (AC #5)

typed-decisions (`uv run scripts/eval/td_score.py quyet-large-Q4`, 400 cases, 2,000 decisions, doc-008 scorer, result `typed_decisions.json`) and the samples (`td_samples.py`, `samples.json`):

| system (saturn, q8_0 KV, sequential, from the Mac) | accuracy | KL from gold | Brier | mean p_max | ECE (scorer) | noul acc | choice acc | score acc | warm p50 (5 questions) | mean input tokens | samples t1 / t5 (median) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TypeSafe Jev 1.13.0 (board, hosted) | 0.727 | 1.442 | 0.148 | | | 0.775 | 0.720 | 0.696 | 0.71 s | | |
| **quyet-large-Q4 (Q4_K_M, 2026-10-08)** | **0.804** | 0.270 | 0.111 | 0.797 | 0.021 | **0.878** | **0.753** | **0.786** | 1.57 s | 1479 | 0.24 to 0.42 s / 0.93 to 1.82 s |
| clef-flash-9b-Q8 | 0.707 | **0.209** | **0.110** | 0.703 | **0.010** | 0.818 | 0.710 | 0.620 | **0.34 s** | **868** | **0.17 to 0.21 s / 0.28 to 0.31 s** |
| winnow-12b-Q8 | 0.702 | 0.629 | 0.238 | 0.858 | 0.156 | 0.788 | 0.657 | 0.671 | 0.79 s | 1721 | 0.16 to 0.30 s / 0.69 to 0.89 s |
| lev-4b-Q8 | 0.637 | 0.297 | 0.165 | 0.639 | 0.043 | 0.757 | 0.617 | 0.562 | 0.58 s | 2464 | 0.25 s / 0.55 s |
| uniform (this scorer) | 0.269 | 0.444 | 0.238 | 0.318 | 0.049 | | | | | | |

Reading: Quyet agrees with the teacher on 0.804 of the decisions, 10 points above Clef-Flash and Winnow and 8 above Jev's own board figure, and leads on every question type. Its probabilities are close to the teacher's spread (KL 0.270, Brier 0.111, mean p_max 0.797 for 0.804 accuracy), so it is nearly as calibrated as Clef-Flash and nothing like Winnow. The cost: one prompt per question on a 31B model. The five-question warm p50 is 1.57 s against 0.34 s for Clef-Flash and 0.79 s for Winnow, and the slowest case took 2.6 s. The first request after a load took 0.94 s (the load itself had already happened in the TypeSafe check). Weakest questions: `agent_trace_observability/action` 0.65, `agent_trace_observability/urgency` 0.66, `customer_service/action` 0.68, `invoice_processing/disposition` 0.70, `security_incidents/urgency` 0.71. Strongest: `customer_service/category` 0.98, `invoice_processing/duplicate` 0.94, `invoice_processing/matches_order` 0.93, `agent_trace_observability/needs_review` 0.92. The weak set is the same as Winnow's (actions and urgency), at a higher level. The gold is a 4B-class teacher, so these figures measure agreement with the teacher, not truth.

Distribution samples, the six rows of decision-002 with Quyet added (first test case of each workflow, options in criteria order, bold marks the gold label):

| question | teacher (gold) | Quyet | Clef-Flash | Winnow |
|---|---|---|---|---|
| agent trace, `risk` (score, 4 levels, label 1) | [0.30, **0.62**, 0.08, 0.01] | [0.19, **0.79**, 0.01, 0.01] | [0.21, **0.64**, 0.07, 0.08] | [0.02, **0.95**, 0.01, 0.02] |
| customer service, `churn_risk` (score, 4 levels, label 1) | [0.10, **0.73**, 0.17, 0.00] | [0.40, **0.58**, 0.01, 0.00] | [0.09, **0.72**, 0.11, 0.08] | [0.02, **0.95**, 0.03, 0.00] |
| security incident, `credential_compromise` (noul, label true) | [0.30, **0.70**] | [0.14, **0.86**] | [0.26, **0.74**] | [0.09, **0.91**] |
| customer service, `needs_human` (noul, label false) | [**0.53**, 0.47] | [**0.54**, 0.46] | [**0.45**, 0.55] | [**0.06**, 0.94] |
| security incident, `severity` (score, 5 levels, label 3) | [0.02, 0.08, 0.37, **0.45**, 0.08] | [0.01, 0.05, 0.09, **0.83**, 0.01] | [0.16, 0.15, 0.37, **0.25**, 0.07] | [0.01, 0.02, 0.06, **0.89**, 0.03] |
| customer service, `category` (choice, 5 options, label delivery) | [0.01, 0.01, **0.92**, 0.05, 0.01] | [0.00, 0.00, **1.00**, 0.00, 0.00] | [0.00, 0.00, **0.73**, 0.14, 0.12] | [0.00, 0.00, **0.99**, 0.00, 0.01] |

Reading: Quyet is right on all six, including `needs_human` where the teacher is split and Quyet reproduces the split (0.54 against 0.53) while Winnow is certain on the wrong side, and `severity` where Clef-Flash misses. Its sharpness varies with the case, like the teacher's and Clef-Flash's: 0.58 on `churn_risk`, 1.00 on `category`. It is sharper than the teacher on the score questions where the teacher spreads over two neighbouring levels.

Throughput, warm medians on the first case of each workflow (`samples.json`, prefix cached, one request at a time, from the Mac):

| case | Quyet t1 / t5 | Clef-Flash t1 / t5 | Winnow t1 / t5 | tokens (5 questions) Quyet / Clef-Flash / Winnow |
|---|---|---|---|---|
| agent_trace_observability | 0.24 / 0.93 s | 0.17 / 0.28 s | 0.16 / 0.79 s | 858 / 736 / 1104 |
| customer_service | 0.41 / 1.27 s | 0.19 / 0.29 s | 0.28 / 0.69 s | 1295 / 892 / 1559 |
| invoice_processing | 0.40 / 1.63 s | 0.19 / 0.31 s | 0.29 / 0.89 s | 1723 / 872 / 1950 |
| security_incidents | 0.42 / 1.82 s | 0.21 / 0.30 s | 0.30 / 0.86 s | 1816 / 927 / 2046 |

One question costs Quyet 1.3 to 2.2 times Clef-Flash's time; five questions cost 3.3 to 6 times. Quyet's prompts are shorter than Winnow's (no system turn, compact JSON) but each one is a 31B forward pass.

## Images (AC #6)

Setup: the manual server at 32k with `--mmproj /opt/llama/models/Quyet-1.0-Large.mmproj-f16.gguf` (the Gemma 4 31B vision tower, from the same mradermacher repo), then the router preset with the same `mmproj` line. The server loads it and reports `input_modalities: ["text", "image"]`; VRAM 22.3 GB after the first image request. Upstream passes the image to mtmd for type `openjev` and the template places one media marker per image before `State:`.

Probe (`image_probe.py`, scratch): a generated 256 px PNG, white with a red disc, as a data URL in `images`, state `{"caption": "A photo was attached."}`, five nouls and two choices about colour, shape and text. The text-only control sends the same request without the image.

| question (gold) | Quyet with image | Quyet text only | Clef-Flash with image | Clef-Flash text only |
|---|---|---|---|---|
| red shape (true) | 0.983 | 0.316 | 0.959 | 0.173 |
| blue shape (false) | 0.008 | 0.245 | 0.003 | 0.137 |
| circle (true) | 0.973 | 0.320 | 0.950 | 0.177 |
| square (false) | 0.020 | 0.346 | 0.005 | 0.174 |
| written text (false) | 0.083 | 0.716 | 0.005 | 0.127 |
| main colour (red) | red 0.995 | red 0.279 | red 0.990 | red 0.348 |
| shape (circle) | circle 0.998 | square 0.632 | circle 0.986 | circle 0.523 |
| warm time, input tokens | 1.76 s, 1041 | 0.54 s, 446 | 0.21 s, 712 | 0.18 s, 645 |

Reading: with the image both models answer all seven correctly and sharply; without it both are near uniform (Quyet's text-only `has_text` 0.72 and `square` 0.63 are guesses from the caption). So the Gemma 4 vision path survives the LoRA merge and the metadata-only conversion, and upstream accepts image requests for this model. Caveat, as the task states: Quyet was trained and evaluated on text only (no image path in `quyet`), so this is a mechanical and one-probe result. It shows that image input works, not how accurate it is on real images. Clef-Flash's image path is trained (ImageJevBench on the board) and 8 times faster here. The image costs Quyet about 85 input tokens per question on top of the text (seven prompts, one image each: 1041 against 446), and the first image request after a load took 1.8 s with 1.7 s on repeats, so the image is encoded once per prompt.

## Decision

See decision-003. Short form: metadata-only conversion with type `openjev` is the route for Quyet, as `nimble` was for Winnow. The 32k context fits the 3090 with q8_0 KV (21.0 GB, 22.3 GB with the mmproj). Quyet replaces Winnow for text accuracy (208 against 198 on JevBench public, 0.804 against 0.702 on typed-decisions) and Clef-Flash for calibration (KL 0.270 against 0.209 is close; Brier equal; JevBench ECE 0.043 against 0.058) and for images (works, with the untested-training caveat). Clef-Flash stays for throughput (five questions in 0.34 s against 1.57 s) and for VRAM headroom (13.8 GB against 22.3 GB). The recommended 3090 configuration is the preset above: Q4_K_M, ctx 32768, q8_0 KV, flash attention, mmproj f16.

## Sources

- `github.com/ncchinh/quyet` at d2514fe (2026-10-08): `src/quyet/llm/prompt.py`, `src/quyet/llm/runtime.py`, `src/quyet/questions.py`, `src/quyet/calibration.py`, `src/quyet/answers.py`, `src/quyet/base.py`, `src/quyet/hub.py`, `tests/test_llm.py`, `README.md`, `NOTICE`.
- `huggingface.co/chinhnc/Quyet-1.0-Large` at 3a3c5e7d (2026-10-08) and revisions e1ecbbe7, da7348f6, 40b9740a: README, `quyet_config.json`, `chat_template.jinja`, `tokenizer.json`, `tokenizer_config.json`, `MANIFEST.sha256`, `generation_config.json`.
- `huggingface.co/mradermacher/Quyet-1.0-Large-GGUF` at 112e27ad (2026-10-05): file list with LFS hashes, README.
- `benchmarkheaven.com/jev-models` (v1.6.1 board, read 2026-10-08) and `benchmarkheaven.com/api/jevbench/v1.6.1`, `/v1.6.0` (the Quyet system record). `quyet.ai`.
- llama.cpp b11429 (`~/Build/llama.cpp` on saturn): `tools/server/server-decision.cpp` (`openjev` labels, `parse_questions`, `render`, `get_temperature`, `format_answer`, image handling), `tools/server/server-common.h` (`common_json` is `ordered_json`), `common/jinja/value.cpp` (`tojson` separators), `common/jinja/lexer.cpp` (trailing newline).
- `github.com/fstandhartinger/jevbench` at c6004e0 (the pinned revision in `scripts/eval/harness.py`), HEAD bb05a33 checked for Quyet mentions.
- doc-005 (the first Quyet analysis), doc-006 (3090 fit estimate), doc-007 (recipe, `gguf_add_decision.py`), doc-008 (protocol and stored results), decision-002.
- Probe files (scratch, not committed): `quyet_prompt.py`, `requests.json`, `replica.json`, `compare_prompts.py`, `image_probe.py`, `typesafe_probe.py`, `convert_and_start.sh`, `vram_and_images.sh`; on saturn, since the 2026-10-08 tidy, `~/Build/numpty-eval/convert/quyet_systemone.jinja` and `~/Build/numpty-eval/probes/nump-022/` (`answers8099.json`, `server8099*.log`, the probe scripts).
