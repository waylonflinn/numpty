---
id: doc-011
title: >-
  One Gemma 4 31B file for chat and decisions: stock Gemma with decision keys,
  Quyet for both roles, and structured output (NUMP-026)
type: specification
created_date: '2026-10-09 14:42'
updated_date: '2026-10-09 16:01'
tags:
  - research
  - decision-models
  - nump-026
---
Research spike NUMP-026, 2026-10-09. Question: for a workload that mixes chat calls and decision calls on the 3090, which Gemma 4 31B file stays resident, and what does that choice cost in decision accuracy and calibration. Decision: decision-005. Protocol: doc-008. Stored results: `scripts/eval/results/gemma-4-31b-Q4-systemone/` and `scripts/eval/results/gemma-4-31b-Q4-systemone-32k/`.

## Summary

- Test A (Quyet serves chat). The `quyet-large-Q4` preset answers `/v1/chat/completions` with the Gemma 4 chat template. With thinking off and greedy decoding the text is normal. With thinking on, or with sampling at the chat preset's temperature, the text degenerates. The cause is the LoRA: it flattened the next-token distribution at the one position it trained (the readout position) and removed the thought-open token. The unmodified Quyet GGUF behaves the same, so the conversion is not the cause. Quyet is not a chat model.
- Test B (stock Gemma with decision keys). A copy of the chat preset's file with the five openjev keys and Quyet's template renders Quyet's prompt byte for byte and serves decisions and chat from one resident file. It scores 179/231 on JevBench public (Quyet 208, Clef-Flash 190) and 0.674 on typed-decisions (Quyet 0.804, Clef-Flash 0.707). The LoRA is worth 29 JevBench items and 13 points of typed-decisions accuracy on the same prompt and the same base model.
- Test C (chat plus structured output). The unmodified chat preset with a strict JSON schema and the jevbench `openai_compat` prompt (the board's cloud route), thinking off, scores 209/231 on JevBench public (Quyet 208) and 0.729 on typed-decisions (Quyet 0.804, Jev 1.13 board 0.727). Its probabilities are verbalized and label-like (216 of 231 JevBench items at p 1.0), so Brier is 0.199 against Quyet's 0.139 on JevBench and 0.181 against 0.111 on typed-decisions, and each question costs a generation: 1.0 s against 0.27 s. The base model answers decisions far better by generating a distribution than by letter readout on Quyet's prompt (209 against 179). What the LoRA buys over this route is 7.5 points on typed-decisions, calibration, and 4 times the throughput. With thinking on, the same route answers 227 of 231 JevBench items (every item that finished, while 4 ran out of the 4,096-token budget), Brier 0.009, but at 3.9 s median and 25 s p95 per question, 14 times Quyet's time. Its typed-decisions figure was not run (about 2 h at that speed).
- Decision (decision-005): two files, with the switch. Quyet stays the decision model and the chat preset stays the chat model. The resident file for a mixed workload is the one the next call needs. The measured cost of one file is the LoRA gap above. The 4 to 5 s switch is the cost of two files.

## Sources (step 0)

- Model card `huggingface.co/chinhnc/Quyet-1.0-Large` at 3a3c5e7d (unchanged since 2026-10-08). It says nothing about chat or generation. It describes the model as "Gemma-4-31B-it with a merged LoRA fine-tune (rank 16), letter-readout decision prompt" that "answers by reading the next-token probabilities of the option letters (A, B, ...) after a fixed prompt", and that it "loads with transformers (and serves with vLLM) as a standard gemma-4-31B-it-architecture checkpoint". It does not say which tokens the loss covers or what data trained it.
- Repository `github.com/ncchinh/quyet` at d2514fe (2026-10-08, two commits). README: "Nothing is generated: every answer is a probability distribution over the options you supplied." No training details, no chat path, no structured-output path.
- llama.cpp b11429 on saturn (`~/Build/llama.cpp`, d81235049). `tools/server/server-context.cpp`: `/v1/systemone` rejects a model without a decision type ("This model is not a decision model"). The chat and completion handlers (`handle_completions_impl`) have no decision check. `server-common.cpp` `server_model_output_modalities()` reports `["decisions"]` for every decision type and `["text"]` otherwise, so `GET /v1/models` shows `decisions` for a decision file even though its chat endpoint works. The Clef note in `models.ini` ("a clef instance serves only /v1/systemone") describes the clef head, not a server gate.
- jevbench c6004e0 `adapters/openai_compat.py`: a chat-completions adapter with a strict JSON schema, `probs_source = "verbalized"`, `temperature 0`, `max_tokens 4096`, a system message and one user message. The board measures cloud models with it. Its prompt is not the systemone prompt. It is the route of test C (see below) because the task names cloud models as the use of the test C row.
- doc-004: the portable schema subset (`object`, `properties`, `required`, `additionalProperties: false`) and the llama.cpp grammar route. The test C schema is inside the subset.
- doc-009: the Quyet mechanism, the template, the five keys, `gguf_add_decision.py`.

## Test A: Quyet as a chat model (AC #3, AC #4)

### Feasibility (AC #3)

The `quyet-large-Q4` preset answers `POST /v1/chat/completions`. The server renders the Gemma 4 chat template from `tokenizer.chat_template`, which the conversion did not touch (the decision template is the separate key `tokenizer.chat_template.systemone`). The default for Gemma 4 on llama-server is thinking on. The switch is `chat_template_kwargs: {"enable_thinking": false}`.

Request (router, 2026-10-09, `chat_probe.py`):

```json
{"model": "quyet-large-Q4", "messages": [{"role": "user", "content": "Why did the chicken cross the road?"}],
 "temperature": 0, "max_tokens": 256, "chat_template_kwargs": {"enable_thinking": false}}
```

Response (shortened): `finish_reason: stop`, 163 completion tokens, 24 prompt tokens, content "The classic answer is: **To get to the other side.**\n\nHowever, depending on who ..." . The same request with `enable_thinking: true` gives `finish_reason: length`, 256 tokens, content "---\n1. **1.0_0_0_0_0_0_0..." and an empty `reasoning_content`.

Four prompts (a joke, a sentence completion, a tool-selection question, a JSON extraction), greedy, 256 tokens, on four files:

| file and flags | thinking off | thinking on |
|---|---|---|
| `quyet-large-Q4` (router, converted file) | 4 of 4 normal: 163 tokens stop, "Paris", `run_tests()` first, correct JSON | 3 of 4 degenerate to the limit ("---\n1. **1.0_0...", "---\n1.0111...", "---\n_1.0_\n_1.0_..."), the JSON extraction survives behind a "---" prefix |
| unmodified `Quyet-1.0-Large.Q4_K_M.gguf` (manual server, Quyet preset flags) | identical text to the row above | identical text to the row above |
| `gemma-4-31B-it-qat-UD-Q4_K_XL.gguf` (manual server, Quyet preset flags) | 4 of 4 normal | 4 of 4 normal, reasoning present |
| `gemma-4-31b-Q4` (router, chat preset) | 4 of 4 normal | 4 of 4 normal, reasoning present |

So the five keys and the systemone template are not the cause, the flags are not the cause, and the chat template renders normally (24 prompt tokens on every file). The LoRA is the cause.

### Mechanism: the LoRA trained one position

Second-token probe (`second_token.py`, manual server, `/completion`, greedy, `n_probs 10`), the probability of the chosen token at the first four generated positions:

| prompt | file | pos 1 | pos 2 | pos 3 | pos 4 |
|---|---|---|---|---|---|
| decision prompt (README `intent`, ends `<channel|>`) | Quyet | `A` 0.037 | `.` 0.902 | ` close` 0.487 | ` the` 1.000 |
| | Gemma chat | `A` 0.559 (`The` 0.413) | `.` 1.000 | ` close` 1.000 | ` the` 1.000 |
| chat, thinking off (ends `<channel|>`) | Quyet | `The` 0.001 | ` classic` 0.600 | ` answer` 0.957 | ` is` 0.893 |
| | Gemma chat | `The` 0.883 | ` answer` 0.985 | ` depends` 1.000 | ` on` 0.978 |
| chat, thinking on (ends `<|turn>model\n`) | Quyet | `---` 0.020 (`<|channel>` 0.001) | `1` 0.001 | `0` 0.010 | `0` 0.028 |
| | Gemma chat | `<|channel>` 1.000 | `thought` 1.000 | `\n` 1.000 | `<channel|>` 1.000 |

Reading. At the readout position (after the empty thought block) Quyet's distribution is flat: the top token holds 0.1 to 4 percent of the mass, where Gemma holds 56 to 88 percent. One position later both models are sharp. The LoRA trained the logits at the readout position only, with a temperature that favors spread over the letters, and the rest of the distribution at that position lost its shape. With the thought block open, Quyet no longer opens a thought (`<|channel>` 0.001) and starts the same "---" sequence. Greedy decoding recovers normal text because the top token at the readout position is still a sensible one. Sampling at the chat preset's temperature 1.0 draws the first token from a flat top-40 and the text is corrupted from the start.

The probe on the eight prompts of the next section (`first_token.py`, router, thinking off, greedy: Quyet's top first token holds 0.000 to 0.055 of the mass on the eight prompts (`'''` 0.001, `'''` 0.040, `Build` 0.001, `'''` 0.012, `2` 0.016, `1` 0.000, `Your` 0.002, `1` 0.055) against 0.58 to 1.00 for the chat preset (`Action` 0.58 on the policy prompt, 0.94 to 1.00 on the rest). From the second token on Quyet is sharp again (0.73 to 1.00 on five of eight prompts)) shows the same shape on every prompt.

Perplexity was planned as the quantified check and is not reported as a figure. `llama-perplexity` b11429 gives PPL 1133 to 3196 for the stock Gemma 4 31B chat file on wikitext-2 (test, sha256 `bbf94c53…574a`, from the Hugging Face `Salesforce/wikitext` parquet) and on War and Peace at every setting tried (ctx 512 and 2048, flash attention on and off, batch 512 and 2048). The tool is broken for Gemma 4 on this build, not the models. The Quyet systemone file and the unmodified Quyet file gave the same PPL (1325 at ctx 2048 by 8 chunks, because the tensors are the same bytes) and the Gemma chat file 1133 at that setting. The ratio is reported with that caveat and nothing is built on it.

### Chat quality (AC #4)

Eight numpty-style prompts with a system message (`chat_quality.py`): a tool choice returned as JSON, a JSON extraction with typed fields, a two-sentence incident summary, a Python function, an arithmetic question, a date-policy question, a two-turn memory question, and a constrained list. `max_tokens 1024`. Five settings. The full requests and replies are in `chat_quality.json` (scratch and saturn `probes/nump-026/`).

| setting | clean replies of 8 | correct of 8 | what went wrong |
|---|---|---|---|
| Quyet, greedy, thinking off | 6 | 6 | tool name rendered as `//1. git_diff`. "502 errorslyly" in the summary. The policy answer counts 100 days (95) but reaches the right action |
| Quyet, `[*]` default sampling (temp 0.2), thinking off | 7 | 6 | the tool choice loops (`1. {\n "tool": "//1. {` ...) to 1024 tokens. The policy answer says "70-90 days (95 days total)" and refuses: right action, broken text |
| Quyet, chat preset sampling (temp 1.0, top-p 0.95, top-k 40), thinking off | 4 | 4 | the tool choice is noise to 1024 tokens. `def median(15):`, "Priyaed", "//Your name". The policy answer says manager approval (wrong) |
| Gemma, greedy, thinking off | 8 | 7 | the policy answer computes 95 days and still says manager approval (wrong) |
| Gemma, chat preset (temp 1.0, thinking on) | 8 | 8 | none. 168 to 453 tokens per reply with the reasoning |

Verdict. Quyet is usable for chat only with greedy decoding and thinking off, and even then one reply in four carries an artifact at the first token. The chat preset's sampling corrupts half of the replies. Thinking, which the chat preset relies on for the policy question, is not available. Quyet-for-both is ruled out for the chat role, not by the decision metrics.

## Test B: the stock chat file with decision keys (AC #1, AC #2)

### Build and parity

`gguf_add_decision.py` (doc-007, unchanged) copied `/opt/llama/models/gemma-4-31B-it-qat-UD-Q4_K_XL.gguf` (the chat preset's file, Unsloth QAT dynamic Q4_K_XL, 17.29 GB) to `gemma-4-31B-it-qat-UD-Q4_K_XL-systemone.gguf` with the five keys of doc-009: `gemma4.decision.type = openjev`, the three Quyet temperatures (choice 1.3007, score 1.3159, noul 1.4957) and `tokenizer.chat_template.systemone` = `quyet_systemone.jinja`. 7 s. 52 keys, 833 tensors, tensors unchanged. No LoRA, no quant change.

Parity: the verbose manual server on the new file rendered the 7 nump-022 requests (`requests.json`) byte-equal to `replica.json`, the quyet package's own renderer, and `usage.input_tokens` equal the replica's counts (203, 184, 87, 91). The live comparison lags one request because the server log is block-buffered (doc-009 noted the same). The full log was compared after the server stopped. So test B sends Quyet's exact prompt to the base model.

Preset `gemma-4-31b-Q4-systemone` in `models.ini` (backup `models.ini.bak-2026-10-09`): the `gemma-4-31b-Q4` lines (128k context, q4_0 KV, `ubatch-size 512`, MTP draft `gemma-4-31B-it-qat-Q4_0-MTP.gguf` with `spec-draft-n-max 3`, temperature 1.0, top-p 0.95, top-k 40) plus `jinja = true`. These are the settings the resident file runs under, which is the question of this task. `GET /v1/models` reports `output_modalities: ["decisions"]`, `input_modalities: ["text"]`. VRAM 23.0 GB with the draft and the 128k q4_0 cache. The MTP draft does not break decisions: the smoke run (`td_score.py --per-workflow 2`) answered every question, and the full run below ran with it.

The same preset still chats: the chicken request through the router returns reasoning and an answer (`finish_reason: length` at 200 tokens, reasoning present). One file, both roles, no switch.

README example through the router, the new preset beside Quyet (doc-009):

| question | stock Gemma + keys | Quyet |
|---|---|---|
| `intent` (choice) | cancel 0.9998 | cancel 0.9966 |
| `urgent` (noul, p true) | 0.986 | 0.721 |
| `mood` (score, calm / annoyed / angry) | 0.9993 / 0.0005 / 0.0002, score 0.001 | 0.770 / 0.219 / 0.011, score 0.24 |

### Results (doc-008 protocol, router, from the Mac, 2026-10-09)

Measured with `td_score.py`, `td_samples.py` and `jevbench.py` unchanged. Results in `scripts/eval/results/gemma-4-31b-Q4-systemone/`.

| model | JevBench correct / 231 | JevBench Brier | JevBench ECE | ordinal MAE | td accuracy | td KL | td Brier | td mean pmax | td ECE | td warm p50 | td input tokens | samples t1 / t5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| quyet-large-Q4 (decision-003) | **208** | **0.139** | **0.043** | **0.171** | **0.804** | 0.270 | 0.111 | 0.797 | 0.021 | 1.57 s | 1479 | 0.24 to 0.42 s / 0.93 to 1.82 s |
| **gemma-4-31b-Q4-systemone (test B, chat preset settings)** | 179 | 0.301 | 0.045 | 0.195 | 0.674 | 0.455 | 0.173 | 0.711 | 0.046 | **1.43 s** | 1479 | 0.24 to 0.41 s / 0.82 to 1.66 s |
| gemma-4-31b-Q4-systemone-32k (test B, Quyet settings: 32k, q8_0 KV, no draft) | 180 | 0.294 | 0.047 | 0.200 | not run | | | | | | | | | | | not run | | | | | | | |
| clef-flash-9b-Q8 | 190 | 0.235 | 0.058 | 0.243 | 0.707 | **0.209** | **0.110** | 0.703 | **0.010** | **0.34 s** | 868 | 0.19 s / 0.30 s |
| winnow-12b-Q8 | 198 | 0.205 | 0.067 | 0.189 | 0.702 | 0.629 | 0.238 | 0.858 | 0.156 | 0.79 s | 1721 | 0.28 s / 0.82 s |

Reading. On the same prompt, the same base model and the same readout, the LoRA is worth 29 JevBench items (208 against 179) and 13 points of typed-decisions accuracy (0.804 against 0.674). The base model is below Clef-Flash and Winnow on both sets. Its JevBench ECE (0.045) equals Quyet's, because it is confident where it is right (103 items above 0.9 confidence at 99 percent accuracy) and spread where it is not (29 items in the 0.4 to 0.5 bin at 38 percent). The Brier gap (0.301 against 0.139) is accuracy, not calibration.

Where the base model loses (JevBench, correct of n, test B against Quyet): multi_hop 9/18 against 15, probability 5/10 against 10, intent 20/24 against 24, long_policy 9/19 against 13, ambiguous 3/7 against 6, routing 9/12 against 12, routing_hard 3/5 against 5. Equal on adequacy, adversarial, extraction, fact, ordinal, tool_selection and trap (all perfect on both), judge_hard (16 against 16) and temporal_numeric (6/15 against 5). Paraphrase agreement 31 of 36 pairs (Quyet 35). typed-decisions by type: noul 0.827 (Quyet 0.878), choice 0.578 (0.753), score 0.632 (0.786). Weakest questions: `agent_trace_observability/action` 0.34 (Quyet 0.65), `security_incidents/severity` 0.41 (0.80), `agent_trace_observability/urgency` 0.51 (0.66), `customer_service/action` 0.52 (0.68), `invoice_processing/disposition` 0.53 (0.70). The base model matches Quyet on the easy binary questions (`duplicate` 0.93, `matches_order` 0.96, `true_positive` 0.89) and loses on the multi-level and action questions.

Throughput is the same file, so the same cost: warm p50 1.43 s for five questions (Quyet 1.57 s, same tokens), t5 0.82 to 1.66 s. The draft does not help decisions (nothing is generated) and does not hurt them.

Distribution samples (first case of each workflow, bold marks the gold label):

| question | teacher | test B | Quyet |
|---|---|---|---|
| agent trace `risk` (score, label 1) | [0.30, **0.62**, 0.08, 0.01] | [0.17, **0.47**, 0.30, 0.06] | [0.19, **0.79**, 0.01, 0.01] |
| customer service `churn_risk` (score, label 1) | [0.10, **0.73**, 0.17, 0.00] | [0.15, **0.83**, 0.02, 0.00] | [0.40, **0.58**, 0.01, 0.00] |
| security `credential_compromise` (noul, true) | [0.30, **0.70**] | [0.20, **0.80**] | [0.14, **0.86**] |
| customer service `needs_human` (noul, false) | [**0.53**, 0.47] | [**0.69**, 0.31] | [**0.54**, 0.46] |
| security `severity` (score, label 3) | [0.02, 0.08, 0.37, **0.45**, 0.08] | [0.09, 0.22, 0.26, **0.42**, 0.00] | [0.01, 0.05, 0.09, **0.83**, 0.01] |
| customer service `category` (choice, delivery) | [0.01, 0.01, **0.92**, 0.05, 0.01] | [0.00, 0.02, **0.98**, 0.00, 0.00] | [0.00, 0.00, **1.00**, 0.00, 0.00] |

The base model is right on all six and flatter than Quyet on the score questions, closer to the teacher's spread on `risk` and `severity`. Its errors are elsewhere (the action and urgency questions above).

Quant caveat. Test B's base is the Unsloth QAT dynamic Q4_K_XL of gemma-4-31B-it. Quyet's file is mradermacher's static Q4_K_M of the merged model. The two quants differ, so the LoRA isolation is approximate. The plan's same-quant check (mradermacher's static Q4_K_M of gemma-4-31B-it, 18.7 GB, available at 69739bb) runs only when the gap is within 5 items. At 29 items a quant difference does not flip the reading.

### Temperature (AC #2)

The stored results use Quyet's temperatures (choice 1.3007, score 1.3159, noul 1.4957), reused, not fitted. Accuracy does not depend on the temperature. The calibration columns of the base model are therefore a lower bound unless the temperature is fitted.

Fit (`fit_temp.py`, scratch). The server computes `softmax(logit / T)` over the k letters, so a stored distribution `p` at `T_q` is rescaled exactly to `T'` by `p' ∝ p^(T_q / T')`. One `T'` per type was fitted by the NLL of the gold label on the first 50 cases of each workflow (300 noul, 300 choice, 400 score decisions) and scored on the other 50 cases (`td_probs.py` recorded the per-decision probabilities in one extra run). A second fit used JevBench easy plus original and scored hard.

| set, type | T Quyet | T fit | held-out KL to gold at T Quyet / T fit | held-out Brier to gold at T Quyet / T fit | held-out ECE (harness, pmax bins) at T Quyet / T fit |
|---|---|---|---|---|---|
| typed-decisions noul | 1.4957 | 2.10 | 0.221 / 0.131 | 0.116 / 0.087 | 0.053 / 0.038 |
| typed-decisions choice | 1.3007 | 2.56 | 0.693 / 0.459 | 0.217 / 0.187 | 0.075 / 0.130 |
| typed-decisions score | 1.3159 | 1.54 | 0.410 / 0.349 | 0.165 / 0.150 | 0.060 / 0.055 |

JevBench. The per-type fit sets are 36, 72 and 12 items. The noul and score fits ran to the grid edge (0.3 and 0.2), that is, they overfit the small split, and the hard split gets worse NLL at the fitted value (noul 0.418 to 0.760). The choice fit lands on 1.30, Quyet's value. Applying the typed-decisions fit to all 231 JevBench items makes the one-hot Brier worse on noul (0.158 to 0.175) and choice (0.383 to 0.401) and better on score (0.249 to 0.243).

Reading. On typed-decisions the base model is sharper than the teacher and a higher temperature helps every type (KL down by a third). On JevBench, which scores against one-hot labels, the same temperatures hurt. The two sets pull in opposite directions and no single temperature improves both. Quyet's values sit between them and are kept for the stored results. The choice ECE rises at the fitted temperature because pmax (0.47) drops below the accuracy (0.58): the fit optimizes NLL, not ECE. The base model's calibration is not the reason it loses to Quyet, and no temperature closes the accuracy gap.

## Test C: chat plus structured output (AC #5)

Run on both sets, as the plan amended: it is the only route for a model that cannot be converted (cloud Sonnet, Luna), so its row is the reference for those models even when it adds nothing against test B.

Route. The unmodified `gemma-4-31b-Q4` chat preset, `POST /v1/chat/completions`, `response_format` with a strict JSON schema (llama.cpp grammar), temperature 0, `max_tokens 4096`, thinking off. The prompt and schema are the jevbench `openai_compat` adapter's, verbatim, so the JevBench row is the board's cloud route and the typed-decisions row (`chat_decide.py`, scratch) sends the same prompt and schema per question and feeds the normalized distribution to the doc-008 scorer unchanged (noul p(yes), choice argmax, score expected level). This differs from the plan's first wording (the systemone prompt content in one user turn). Reason: step 0 found the board's adapter, and the test C row is for comparison with cloud models that the board measures with that adapter.

Prompt (system message, then one user message):

```
You are a calibration engine. You never answer in prose. You output only a JSON object with the key 'probabilities' mapping every given option to a probability, all options included, values in [0,1], summing to 1.
```

```
State:
{state as it is, or the JSON object with ensure_ascii=False}

{instructions}

Options:
- {label}: {description}      (one line per option. noul labels are "no" and "yes" with the false / true descriptions. A label without a description is "- label")

Output probabilities over exactly these keys: ["label", ...].
```

Score questions replace the Options block with `Levels:` (`0: description` per level) and `Rate the state. Output probabilities over the level indices: ["0", ...].`

Schema (`strict: true`, name `distribution`):

```json
{"type": "object", "required": ["probabilities"], "additionalProperties": false,
 "properties": {"probabilities": {"type": "object", "required": [labels], "additionalProperties": false,
                                  "properties": {"<label>": {"type": "number"}}}}}
```

Invalid or unparseable JSON counts as a uniform answer and is counted in the schema validity column. The probabilities are verbalized by the model in its output text, not read from logits, so the calibration columns are comparable with test B and Quyet in outcome only, not in mechanism.

| route (saturn, router, from the Mac) | JevBench correct / 231 | JevBench Brier | JevBench ECE | ordinal MAE | paraphrase pairs agree / 36 | td accuracy | td KL | td Brier | td mean pmax | td ECE | schema valid | output tokens per decision | latency per question p50 / p95 | five-question case |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| quyet-large-Q4 (logit readout) | 208 | **0.139** | **0.043** | **0.171** | 35 | **0.804** | **0.270** | **0.111** | 0.797 | **0.021** | n/a | 0 | **0.27 s / 2.40 s** | **1.57 s** |
| gemma-4-31b-Q4-systemone (test B, logit readout) | 179 | 0.301 | 0.045 | 0.195 | 31 | 0.674 | 0.455 | 0.173 | 0.711 | 0.046 | n/a | 0 | 0.29 s / 2.30 s | 1.43 s |
| **gemma-4-31b-Q4, chat + schema, thinking off (test C)** | **209** | 0.199 | 0.109 | 0.283 | 34 | 0.729 | 0.851 | 0.181 | 0.818 | 0.089 | 1.000 (231 and 2,000) | 58 (JevBench), 47 (td) | 1.05 s / 3.44 s (JevBench), 1.00 s / 1.37 s (td) | about 5 s |
| gemma-4-31b-Q4, chat + schema, thinking on (test C, JevBench only) | 227 (all 227 that answered. 4 hit the 4,096-token limit while thinking and count as wrong) | 0.009 | 0.015 | 0.003 | 36 | not run | | | | | 0.983 | 567 mean, 315 median, 4,096 max | 3.86 s / 25.0 s (failures 48 s) | not run, about 20 s by the per-question figure |
| clef-flash-9b-Q8 | 190 | 0.235 | 0.058 | 0.243 | | 0.707 | 0.209 | 0.110 | 0.703 | 0.010 | n/a | 0 | 0.22 s / 0.86 s | 0.34 s |

Caveat on every calibration column of the test C rows: the probabilities are verbalized, not logit-derived. They are comparable with Quyet and test B in outcome (the scorer is the same), not in mechanism.

Reading.

- Accuracy. The chat route matches Quyet on JevBench (209 against 208: 8 items only the chat route gets, 7 only Quyet, 15 both miss) and is 7.5 points behind on typed-decisions (0.729 against 0.804), where it loses on 17 of 20 questions, most on the action and urgency questions (`agent_trace_observability/action` 0.41 against 0.65, `urgency` 0.49 against 0.66). It beats test B, the same base model with letter readout on Quyet's prompt, by 30 JevBench items and 5.5 typed-decisions points, on 16 of 20 questions. The base model is a better decision model when it generates than when its letter logits are read on a prompt it never trained on.
- Sharpness. The distributions are labels with a few hedges: 216 of 231 JevBench items and 318 of 2,000 typed-decisions answers at p 1.0, 13 and 17 distinct pmax values, 97.6 and 95.9 percent of all values on the 0.05 grid. The JevBench ECE (0.109) is the 22 wrong items at p 1.0. On typed-decisions the KL to the teacher is 0.851 (Quyet 0.270) because a label puts near-zero mass where the teacher spreads.
- Cost. Each question is a generation of about 50 tokens: 1.0 s per question against 0.27 s, so a five-question case costs about 5 s against 1.57 s. Input tokens are fewer (390 per question on typed-decisions against 1,479 per five-question case, since the state repeats per question but the prompt is shorter), and the prefix cache holds the state across the five questions.
- Thinking on (JevBench only). 227 of 231: every item that produced JSON was correct, paraphrase agreement 36 of 36, long_policy 17/19 (Quyet 13), temporal_numeric 13/15 (Quyet 5). The four failures are two long_policy and two temporal_numeric items that were still thinking at 4,096 tokens (48 s each). jevbench counts them as wrong. 567 output tokens per item on average (median 315, max 3,767 on an item that finished). Latency p50 3.9 s, mean 7.1 s, max 43 s on finished items, p95 25 s over all. The distributions are still labels (215 of 227 at p 1.0). This is the accuracy ceiling of the three routes on JevBench public and the slowest by far. typed-decisions was not run on it: 2,000 questions at 4 to 7 s is about 3 h, outside the session.
- Thresholds. The thinking-off chat route passes the 5-item JevBench margin and fails the 0.02 typed-decisions accuracy margin (gap 0.075) and the 0.01 Brier margin on both sets. The thinking-on route exceeds Quyet on JevBench accuracy and one-hot Brier, is unmeasured on typed-decisions, and costs 14 times the latency.

## Decision (AC #6)

See decision-005. Thresholds were fixed before measuring (plan step 7): the stock file with decision keys stays resident if it is within 5 JevBench items and 0.02 typed-decisions accuracy of Quyet and its fitted-temperature calibration is within 0.01 Brier. The structured-output route is named only if it matches that within the same margins and the metadata route is unwanted. Otherwise two files with the measured switch.

| candidate for a mixed workload | JevBench / 231 | td accuracy | chat | cost against Quyet |
|---|---|---|---|---|
| Quyet for both roles (thinking off, greedy) | 208 | 0.804 | artifacts in 1 of 4 greedy replies, corrupt at the chat preset's sampling, no thinking | the chat role |
| stock Gemma with decision keys (test B) | 179 | 0.674 | the chat preset, unchanged | 29 items, 13 points |
| stock Gemma, chat plus structured output, thinking off (test C) | 209 | 0.729 | the chat preset, unchanged | 1 item ahead on JevBench, 7.5 points behind on typed-decisions, Brier 0.06 to 0.07 worse (verbalized), 4 times the latency per question |
| stock Gemma, chat plus structured output, thinking on (test C) | 227 (4 token-limit failures) | not run | the chat preset, unchanged | 19 items ahead on JevBench, Brier 0.009 (labels), 14 times the latency per question (3.9 s median, 25 s p95), typed-decisions unmeasured |
| two files, the switch | 208 | 0.804 | the chat preset, unchanged | a 4.6 s load for Quyet and a 4 to 5 s load for the chat preset at every role change |

No one-file route is within the thresholds on both sets. The thinking-off chat route fails typed-decisions accuracy and calibration. The thinking-on chat route beats Quyet on JevBench but is unmeasured on typed-decisions and 14 times slower. Decision: two files. Quyet (`quyet-large-Q4`) stays the decision model and `gemma-4-31b-Q4` the chat model, with the switch. The thinking-on structured-output route is the named route when accuracy outranks latency and the chat file must stay resident, and its typed-decisions measurement is the open item that can reopen the decision. Reopen conditions are in decision-005.

## Probe files

Scratch (this session) and saturn `~/Build/numpty-eval/probes/nump-026/`: `chat_probe.py` and `chat_probe*.json` (test A, four prompts), `second_token.py` and `second_token_*.json`, `chat_quality.py` and `chat_quality.json` (AC #4), `first_token.py` and `first_token.json`, `step1.sh`, `step2.sh` and their logs, `server8099-*.log`, `ppl-*.log`, `wikitext/wiki.test.raw`, `answers8099-gemma-so.json` (parity answers), `router-readme-gemma-so.json`, `td_probs.py` and `td_probs_gemma-4-31b-Q4-systemone.json`, `fit_temp.py` and `fit_temp_B.json`, `chat_decide.py`, `jev_chat.sh` and `test-c/` (test C raw and summaries). JevBench raw runs: `scripts/eval/data/runs/jevbench-gemma-4-31b-Q4-systemone/`, `jevbench-gemma-4-31b-Q4-systemone-32k/`, `jevbench-gemma-4-31b-Q4-nothink/`, `jevbench-gemma-4-31b-Q4-think/` (not committed). The converted file `gemma-4-31B-it-qat-UD-Q4_K_XL-systemone.gguf` and the two presets stay on saturn. Nothing in `scripts/eval/` changed. A follow-up to promote `chat_decide.py` into `scripts/eval/` is not created here.

## Appendix: the AC #4 prompts and the greedy replies

System message on every prompt: "You are numpty, a careful coding and operations assistant. Answer briefly. When asked for JSON, return only JSON." Settings: `temperature 0`, `max_tokens 1024`, `enable_thinking false`. The other three settings and the full responses are in `chat_quality.json`.

### tool_pick

user:

```
Tools: read_file(path), run_tests(), git_diff(), web_search(query). The user says: 'the unit tests started failing after my last edit to parser.py'. Reply with JSON {"tool": name, "args": {...}, "why": one sentence}.
```

Quyet, greedy, thinking off (66 tokens, finish stop):

```
```json
 {
  "tool": "//1. git_diff",
  "args": {
   "path": "parser.py"
  },
  "why": "I need to see the changes made to parser.py to understand why the tests are failing."
 }
```
```

Gemma chat preset, greedy, thinking off (47 tokens, finish stop):

```
```json
{"tool": "git_diff", "args": {"path": "parser.py"}, "why": "To identify the specific changes made to parser.py that caused the tests to fail."}
```
```

### extract

user:

```
Extract JSON with keys name, order_id (integer), issue, wants_refund (boolean) from: 'Hi, Dana Reyes here. Order 48213 arrived with a cracked lid, I just want a replacement, not my money back.'
```

Quyet, greedy, thinking off (51 tokens, finish stop):

```
```json
{
  "name": "Dana Reyes",
  "order_id": 48213,
  "issue": "cracked lid",
  "wants_refund": false
}
```
```

Gemma chat preset, greedy, thinking off (51 tokens, finish stop):

```
```json
{
  "name": "Dana Reyes",
  "order_id": 48213,
  "issue": "cracked lid",
  "wants_refund": false
}
```
```

### summarize

user:

```
Summarize in two sentences: 'The deploy at 14:02 UTC rolled out build 7f3a to 30% of pods. Error rate rose from 0.4% to 2.1% within six minutes, dominated by 502s from the checkout service. The on-call engineer paused the rollout at 14:11 and rolled back at 14:19; error rate returned to baseline by 14:24. Root cause: a connection-pool size default changed from 32 to 8.'
```

Quyet, greedy, thinking off (71 tokens, finish stop):

```
Build 7f3a caused checkout service 502 errorslyly, increasing the error rate to 2.1% after deployment to 30% of pods. The rollout was rolled back by 14:19 after it was discovered that a connection-pool size default had changed from 32 to 8.
```

Gemma chat preset, greedy, thinking off (50 tokens, finish stop):

```
Build 7f3a caused a spike in checkout service 502 errors due to a connection-pool size reduction. The rollout was paused and rolled back, restoring the error rate to baseline by 14:24 UTC.
```

### code

user:

```
Write a Python function `median(xs)` that returns the median of a non-empty list of numbers without importing anything. Code only.
```

Quyet, greedy, thinking off (71 tokens, finish stop):

```
```python
def median(xs):
    s = sorted(xs)
    n = len(s)
    m = n // 2
    if n % 2 == 0:
        return (s[m-1] + s[m]) / 2
    return s[m]
```
```

Gemma chat preset, greedy, thinking off (52 tokens, finish stop):

```
```python
def median(xs):
    s = sorted(xs)
    n = len(s)
    m = n // 2
    return (s[m] + s[~m]) / 2
```
```

### arith

user:

```
A job processes 1,479 tokens per request at 0.3 s per request. How many requests and how many tokens in 10 minutes? Show the two numbers.
```

Quyet, greedy, thinking off (18 tokens, finish stop):

```
2,000 requests
2,958,000 tokens
```

Gemma chat preset, greedy, thinking off (22 tokens, finish stop):

```
Requests: 2,000
Tokens: 2,958,000
```

### policy

user:

```
Policy: refunds within 30 days need no approval; 31 to 90 days need a manager; after 90 days refuse. A customer bought on June 2 and asks for a refund on September 5. What is the correct action and why?
```

Quyet, greedy, thinking off (13 tokens, finish stop):

```
100 days have passed. Refuse the refund.
```

Gemma chat preset, greedy, thinking off (108 tokens, finish stop):

```
Action: Manager approval required.
Why: The period from June 2 to September 5 is 95 days, but calculating by calendar months (June 2 to Sept 2) is 3 months. Specifically, June (28 days left) + July (31) + August (31) + Sept (5) = 95 days.

*Correction:* Since it is 95 days, the correct action is **Refuse**, as it exceeds the 90-day limit.
```

### multiturn

user:

```
My name is Priya and I run a bakery.
```

assistant:

```
Nice to meet you, Priya. How can I help with the bakery?
```

user:

```
What is my name and what should I call my new sourdough loaf? One name, one sentence.
```

Quyet, greedy, thinking off (19 tokens, finish stop):

```
Your name is Priya, and you should call your sourdough loaf "11th Hour."
```

Gemma chat preset, greedy, thinking off (17 tokens, finish stop):

```
Your name is Priya, and you should call your loaf "The Golden Crust."
```

### constrained

user:

```
List five Unix commands for finding text in files. Format: a numbered list, each line 'command: purpose', nothing else.
```

Quyet, greedy, thinking off (52 tokens, finish stop):

```
1. grep: search for patterns in files
2. zgrep: search for patterns in compressed files
3. awk: pattern scanning and processing
4. sed: stream editor for filtering patterns
5. ripgrep: recursive search with regex
```

Gemma chat preset, greedy, thinking off (52 tokens, finish stop):

```
1. grep: search for patterns in files
2. egrep: search using extended regular expressions
3. fgrep: search for fixed strings (faster)
4. awk: pattern scanning and processing
5. sed: stream editing and searching
```
