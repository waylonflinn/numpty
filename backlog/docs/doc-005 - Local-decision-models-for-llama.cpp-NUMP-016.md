---
id: doc-005
title: Local decision models for llama.cpp (NUMP-016)
type: other
created_date: '2026-10-05 21:41'
updated_date: '2026-10-08 19:26'
tags:
  - research
  - decision-models
---
# Local decision models for llama.cpp (NUMP-016)

Evaluation scripts, protocol and stored results: doc-008 - Decision model evaluation protocol (`scripts/eval/`).

Research for NUMP-016, in preparation for NUMP-007 (Jev support). Facts verified on 2026-10-05 and 2026-10-06 unless marked "claimed". Probe scripts live in the session scratch directory and are not committed. The recurrent cross-reference with the JevBench board and the RTX 3090 fit table is doc-006; this doc does not repeat those tables. The decision this research feeds is decision-001.

## Test environment

- llama-server: `https://saturn.wayforwardlabs.com`. LAN host with one RTX 3090 (24 GB). Built from llama.cpp GitHub main on 2026-10-05, build `b11429-d81235049`, v0.6.0-dev (reported by `GET /props`).
- Models are swapped through the `models.ini` router (`--models-max 1`). Chat test models: `qwen-38-27b-Q4`, `gemma-4-31b-Q4`. Decision models installed 2026-10-06: `lev-4b-Q8` (ctx 32768) and `clef-flash-9b-Q8` (ctx, batch, and ubatch 16384; mmproj loaded, so images work). Both presets use `cache-type-k/v = q8_0` and flash attention.
- The server handles one request at a time. Do not send concurrent requests.
- The local Homebrew `llama-server` on the Mac is 0.5.0 (build 11146). It has no `/v1/systemone`. Do not use it for this work.
- Apple Silicon reference machine for the memory estimate: M3 Pro, 36 GB unified memory. No decision model was run on it.

## llama.cpp native decision models (verified)

llama.cpp v0.6.0 added `POST /v1/systemone`, a TypeSafe-compatible System One API (PR ggml-org/llama.cpp#29818, merged 2026-10-02, first build b11361). The earlier proposal to emulate decisions with a grammar and `n_probs` (discussion #29269) was not taken up; see "Fallback for chat models" below.

How the server detects a decision model:

- GGUF key `{arch}.decision.type` with one of: `openjev`, `lev`, `kev`, `nimble`, `laya`, `clef`. Keys `{arch}.decision.temperature.{choice|score|noul}` hold per-type softmax temperatures. A `{type}.{bucket}` key can override by option count (buckets `2`, `3_5`, `6_10`, `11`, or `small`/`mid`/`large` for lev).
- A named chat template `tokenizer.chat_template.systemone`. The server renders it with `state`, `instructions`, `type`, `options[{key, description, label?}]`, `id`, `images`.
- `GET /v1/models` reports `architecture.output_modalities: ["decisions"]` for such a model without a load. Verified on saturn for `lev-4b-Q8` and `clef-flash-9b-Q8`; every chat model reports `["text"]`.
- A request to a non-decision model returns HTTP 501 `{"error":{"code":501,"message":"This model is not a decision model","type":"not_supported_error"}}`. Verified on saturn with `gemma-4-31b-Q4`.

Decision types (from `common/common.h` and `tools/server/server-decision.cpp`):

| type | mechanism | option limit | notes |
|---|---|---|---|
| openjev | logit of one single-token letter per option (A-Z, a-z), read at the last prompt token | 52 | noul renders true first |
| lev | same as openjev, labels A..Z then AA..ZZ (single-token only) | up to 255 | noul read from a rating scale, choice shown in two orders and averaged |
| nimble | same as openjev, prompt lists all questions | 52 | |
| kev | dot product of last-token hidden state with the hidden state at each option's `<|box_end|>` | 255 | text-only input, special tokens escaped |
| laya | encoder, score of one `[MASK]` marker per option from the embeddings output | 255 | options and question truncated to `max_head_tokens` |
| clef | encoder, all questions in one prompt, answered jointly | 255 | the server then serves only this endpoint |

Answer math (`server-decision.cpp`): softmax of the per-option scores divided by the temperature. `confidence` uses the formulas TypeSafe published. Choice: `(p_max - 1/n) / (1 - 1/n)`. Score: `1 - mean distance to the mode / that of a uniform distribution`. Score `score` is the probability-weighted level index. The README states the probabilities "are not guaranteed to be calibrated for your data".

## Catalog (AC #1)

Native models: every repo in the ggml-org Hugging Face collection "Decision models" (8 repos, collection last updated 2026-10-04). Sizes, quants, GGUF header keys, and the JevBench match evidence are in doc-006; this table adds the limits and the published scores. "State limit" is the model's own card figure; llama-server itself only enforces the context size of the loaded model (`-c`) and, for laya and clef, `--ubatch-size`.

| model (GGUF repo) | type | base model | params | question types | option limit | state limit (card) | license | JevBench v1.6.0 (Capability, rank) | typed-decisions (400 cases, 2,000 decisions) |
|---|---|---|---|---|---|---|---|---|---|
| Julia-1 (`ggml-org/Julia-1-GGUF`) | laya | mmBERT-small (SupersonicLabs/Julia-1) | 144M | choice, score, noul | 2 to 20 (card); 255 (server), head budget 256 tokens | 8,192 combined tokens; each option 48 tokens | Apache-2.0 | not measured | 73.15% accuracy claimed on the card (Jev reference 72.70%); not on the dataset's own board |
| Laya (`ggml-org/Laya-GGUF`) | laya | ModernBERT-large (convaiinnovations/laya, English root) | 421M | choice, score, noul | 255 (server), head budget 192 tokens; card warns above 20 options | 512 tokens default (about 320 for state); multilingual checkpoint 8,192 | Apache-2.0 | 32.5, #84 (I 1.8) | 0.362 zero-shot (card); 0.766 only for the `laya-typed-decisions` checkpoint fitted on `train`, which is not this GGUF |
| Kev-4B (`ggml-org/Kev-4B-GGUF`) | kev | Qwen3.5-4B-Base (jaredpalmer/kev-4b) | 4.2B | choice, score (1 to 255 levels on the card; server caps score at 10), noul | 255 | 65,536 served, 8,192 validated; training states at most 7,552 | Apache-2.0 | not measured (board row "kev 4B" is the Qwen3 predecessor) | not on the board; card reports 0.838 on its own locked typed-decision set |
| lev (`ggml-org/lev-GGUF`) | lev | Qwen3.5-4B + LoRA r32 (interfaze-ai/lev) | 4.2B | choice, score (2 to 10), noul | 255 (single-token labels A..ZZ) | none stated; Qwen3.5 context | Apache-2.0 | 61.7, #14, Jev-class | not on the board; measured here, see below. S1Bench macro 0.689 vs Jev 0.761 (card) |
| Clef-Flash (`ggml-org/Clef-Flash-GGUF`) | clef | Qwen3.5-9B + joint schema head (Cloudflare/clef-flash) | 9.1B | choice, score, noul; images and video | 255 | 16,384 tokens default `max_length` (card); whole prompt must fit `--ubatch-size` | Apache-2.0 | 63.8, #21, Jev-class | not on the board; measured here, see below. Typesafe Evals workflows 57.1 to 77.0 vs Jev 61.8 to 83.1 (card) |
| Clef (`ggml-org/Clef-GGUF`) | clef | Qwen3.8-27B + joint schema head (Cloudflare/clef) | 27B | choice, score, noul; images and video | 255 | 16,384 tokens default `max_length` (card) | Apache-2.0 | 75.3, #43 (Composite floored by H100 cost) | not on the board; Typesafe Evals workflows 62.9 to 86.2 vs Jev (card) |
| OpenJev (`ggml-org/OpenJev-GGUF`) | openjev | Qwen3.8-27B (openjev/openjev) | 27B | choice, score, noul; one image | 52 per pass (server limit 52) | prompts up to 16,384 tokens (card) | CC-BY-NC-4.0 | not measured (board "OpenJev" rows are other projects) | not on the board; card claims 84.0% on its own 10,000 questions, Jev 85.4% on the same set; Q4_K_M 82.8% on 1,789 held-out |
| Bespoke-Nimble-9B-v3 (`ggml-org/Bespoke-Nimble-9B-v3-GGUF`) | nimble | Qwen3.5-9B LoRA merged | 9.0B | choice, score, noul | 52 | none stated | CC-BY-NC-4.0 | 56.5, #33 | not on the board |

TypeSafe Jev 1.13.0 for reference: 255 options per Choice, 2 to 10 Score levels, 64k tokens per request and 32k for state plus the longest question, text only, Capability 76.5 and rank #2 on JevBench v1.6.0, typed-decisions accuracy 0.727 with KL 1.442 (board, measured 2026-09-18).

Other GGUF-available System One models, checked 2026-10-06. None is a llama.cpp decision model; all would need their own server or a metadata conversion:

| model | base | license | GGUF | llama.cpp decision metadata | JevBench v1.6.0 | note |
|---|---|---|---|---|---|---|
| JevK5 v0.3 (`alibiserikbay/JevK5`) | Qwen3.5-4B + distilled LoRA, merged | Apache-2.0 | none in the repo (safetensors only); JevK5-9B also safetensors | n/a | Capability 64.2, #18 | own `/v1/systemone` server (`github.com/allebee/jevk5`), letter readout |
| decider-4b v2.1 (`Mapika/decider-4b-GGUF`) | Qwen3.5-4B | Apache-2.0 | BF16 8.4 GB, Q4_K_M 2.7, Q8_0 4.5 | none: header is plain `qwen35`, no `decision.type`, no `systemone` template (read 2026-10-06) | decider-4b v2: Capability 64.9, #17 | own server over llama-cpp-python |
| decider-2b v11 (`Mapika/decider-2b-GGUF`) | Qwen3.5-2B | Apache-2.0 | BF16 3.8, Q4_K_M 1.3, Q8_0 2.0 | none (same check) | not matched | same |
| Quyet-1.0-Large (`mradermacher/Quyet-1.0-Large-GGUF`) | Gemma-4-31B-it | Apache-2.0 | Q4_K_M and others | none; mechanism matches `openjev`, patch requirements below | Capability 81.7, #1 | 31B: tight on the 3090 at Q4 (doc-006) |
| Winnow-12B (`EldanRing/Winnow-12B`) | Gemma-4-12B-it LoRA merged | Apache-2.0 | Q8_0 12.7 GB, NVFP4 8.2 | none (doc-006); author's llama.cpp fork serves it | Capability 71.2, #6 | top watch item in doc-006 |
| OpenSourceJev (`github.com/sabeel111/OpenSourceJev`) | Qwen3.5-4B Q4_K_M (unsloth GGUF) | MIT code, Apache-2.0 weights | plain chat GGUF | none; the project's "native llama.cpp" is its own grammar and logprob wrapper | Capability 48.6, #52 | below lev with the same base |

Encoder models (Julia-1, Laya) are the fastest and smallest but truncate questions and options to a head budget and cap the state at 8k or less. Decoder models (lev, Kev, OpenJev, Nimble) take long states and up to 255 options. Clef models answer all questions jointly and lock the server to this endpoint.

## Wire contract: llama-server vs TypeSafe (AC #2)

Sources: llama-server `tools/server/README.md` section "POST /v1/systemone" (master, read 2026-10-06), `docs.typesafe.ai/api` and `docs.typesafe.ai/models` (read 2026-10-06), `typesafe-sdk` 0.7.2 source, and probes against saturn `lev-4b-Q8` on 2026-10-06 (`sdk_probe.py`, scratch).

Request:

| field | TypeSafe | llama-server | verified on saturn |
|---|---|---|---|
| `state` | string, object, or array; required | same; non-strings are given to the model as JSON text | object state accepted |
| `model` | string, required (`jev-latest`, `jev-1.13.0`, ...) | string, required when the router is used: a missing name returns 400 "model name is missing from the request"; unknown name returns 400 "model '...' not found"; a chat model returns 501 | yes |
| `questions` | map id to question, required | same; empty or missing returns 400 `"questions" must be a non-empty object` | yes |
| `type` | `choice`, `score`, `noul` | same; other values return 400 | yes |
| `instructions` | string, object, or array, required | required; object accepted | yes |
| choice `criteria` | map option to description or null; at most 255 options | same; non-empty object required; limit depends on the model (lev 255, openjev 52) and over the limit returns 400 "too many options (300), this model supports at most 255" | yes; 60 options answered; 1 option answered with confidence 1.0 |
| score `criteria` | array of 2 to 10 levels | same; 1 or 11 levels return 400 | yes |
| noul `criteria` | optional `{true, false}` descriptions | same, optional | yes |
| `images` | not in the API (Jev is text only) | extension: array of data URLs; also `image_url` parts inside a chat-message `state` | yes, on clef-flash with mmproj (session 2) |
| auth | `Authorization: Bearer <key>`, required | none required; a Bearer header is ignored unless the server was started with `--api-key` | request without any auth header accepted; with a dummy Bearer accepted |
| headers `X-TypeSafe-SDK`, `X-TypeSafe-Runtime`, `X-TypeSafe-Retry-Count` | sent by the SDK | ignored | SDK requests succeed |
| streaming | none | none | n/a |

Response:

| field | TypeSafe | llama-server | verified |
|---|---|---|---|
| `model` | versioned id that answered, for example `jev-1.13.0` | the router alias, for example `lev-4b-Q8` | yes |
| `answers.<id>.type` | present | present | yes |
| choice: `choice`, `probabilities`, `confidence` | present | present, same formula | yes |
| score: `score`, `legend` (string keys), `probabilities` (string keys), `confidence` | present | present | yes |
| noul: `noul` | present | present | yes |
| `usage.input_tokens` | tokens | prompt tokens of all questions; for lev each question is a separate prompt, so one 488-token request counts the state once per question | yes |
| `usage.output_tokens` | small positive numbers in the docs (18 to 34) | always 0 | yes |
| `x-typesafe-request-id` header | present | absent; SDK `request_id` is `None` | yes |

Errors:

| case | TypeSafe status | llama-server status and body | SDK exception against llama-server |
|---|---|---|---|
| bad or missing field, bad question | 422, body names the field | 400 `{"error":{"code":400,"message":"questions.a: ...","type":"invalid_request_error"}}` | `TypeSafeBadRequestError` (TypeSafe would raise `TypeSafeUnprocessableEntityError`) |
| not JSON | 422 | 400 with the nlohmann parse error | `TypeSafeBadRequestError` |
| unknown model | 422 (validation) | 400 "model 'x' not found" | `TypeSafeBadRequestError` |
| model cannot decide | n/a | 501 `not_supported_error` | `TypeSafeInternalServerError` (the SDK maps every 5xx to it) |
| missing or bad key | 401 | 401 only with `--api-key` | `TypeSafeAuthenticationError` |
| rate limit, overload | 429, 529 with retry-after; SDK retries | the router queues; no 429 seen | n/a |

The SDK's `extract_message` reads `error.message` from the body, so llama-server's error text reaches the exception message unchanged: `400 model 'no-such-model' not found`, `501 This model is not a decision model`.

`GET /v1/models`: TypeSafe returns `{"models": [{name, description, release_date}]}`. llama-server returns the OpenAI shape `{"object": "list", "data": [{id, object, owned_by, status, architecture}]}`. `client.models.list()` against saturn raises `TypeSafeAPIResponseValidationError("200 Invalid response data at 'models'")`. The llama-server shape carries the field numpty needs to pick a decision model, `architecture.output_modalities == ["decisions"]`, which TypeSafe does not have.

Verdict: one client can target both for `system_one`. `typesafe-sdk` 0.7.2 with `base_url` pointed at saturn, a dummy `api_key` (the SDK refuses an empty key), and `model` set to the router alias answered the README example correctly through the normal `SystemOneResponse` path, cold 2.0 s (model load), warm 0.23 s. The same holds for llmman and the other `/v1/systemone` hosts (meraGPT, Liquid) that the typed-decisions board names. A stdlib HTTP client needs the same three request fields and the same response parser. The differences a client must tolerate: 400 instead of 422 for validation, 501 for a non-decision model, `output_tokens` 0, no request id, no `models.list()` compatibility, and model-specific option limits (52 for openjev and nimble). None of them needs a per-vendor code path in the request or answer shape. The SDK brings pydantic, httpx2, and tenacity. numpty core has no dependencies, but the OpenAI and Anthropic SDKs are already optional extras, and `OpenAIChat` already takes a placeholder `api_key` for llama-server, so the SDK as a `numpty[typesafe]` extra follows the existing pattern; decision-001 recommends it and leaves the final call to NUMP-007.

## Measurements on saturn (AC #4)

### README example (choice, noul, score; one request)

Measured 2026-10-06 through the router. VRAM from `nvidia-smi` on the host. Cold includes the model load.

| model | cold | warm | VRAM | input tokens | choice | score | noul |
|---|---|---|---|---|---|---|---|
| lev-4b-Q8 (ctx 32k) | 2.0 s | 0.18 to 0.23 s | 5.7 GB | 488 | billing 0.93, confidence 0.89 | 1.59, confidence 0.20 | 0.56 |
| clef-flash-9b-Q8 (ctx 16k, text) | 3.2 s | 0.25 s | 10.7 GB | 324 | billing | 2.21 | 0.42 |
| clef-flash-9b-Q8 with mmproj, one 256 px image | 3.7 s | 0.34 s | 13.9 GB | 372 | colour and shape nouls at 0.98, has_text 0.003 | | |

### typed-decisions, full test split

`LocalLLaMA/typed-decisions` (Apache-2.0, updated 2026-10-01), config `all`, split `test`: 400 cases, 2,000 decisions, five questions per case sent in one request, exactly as the board does. Scorer in scratch (`td_probe.py`): accuracy of the highest-probability option against the gold label, KL from the gold distribution, multi-class Brier (sum of squared differences). The scorer's uniform baseline reproduces the board's published uniform row on KL (0.444) and Brier (0.238), so the columns are comparable; its accuracy baseline differs (0.269 vs 0.308) only in how ties are broken. Sequential requests, one model resident, Q8_0 weights with q8_0 KV cache, so this is a quant and KV mismatch against the board's hosted rows.

| system | accuracy | KL from gold | Brier | noul acc | choice acc | score acc | warm p50 | cold | mean input tokens | VRAM |
|---|---|---|---|---|---|---|---|---|---|---|
| meraGPT Decider 1 (board, hosted) | 0.768 | 0.096 | 0.052 | 0.840 | 0.733 | 0.739 | 526 ms | | | |
| TypeSafe Jev 1.13.0 (board, hosted, 2026-09-18) | 0.727 | 1.442 | 0.148 | 0.775 | 0.720 | 0.696 | 710 ms | | | |
| **clef-flash-9b-Q8 on saturn** | **0.707** | **0.209** | **0.110** | 0.818 | 0.710 | 0.620 | 0.37 s | 3.7 s | 868 | 13.5 GB (with mmproj) |
| OpenDecider-small (board, self-reported) | 0.671 | 0.211 | 0.117 | | | | 40 ms | | | |
| **lev-4b-Q8 on saturn** | **0.637** | **0.297** | **0.165** | 0.757 | 0.617 | 0.562 | 0.58 s | 0.8 s | 2,464 | 5.7 GB |
| Bongard-mini (board, self-reported) | 0.594 | 0.256 | 0.132 | | | | | | | |
| Prior (board: train label frequencies) | 0.470 | 0.347 | 0.189 | | | | | | | |
| Uniform (board / this scorer) | 0.308 / 0.269 | 0.444 / 0.444 | 0.238 / 0.238 | | | | | | | |

Reading: Clef-Flash lands 2 points under Jev on accuracy and far closer to the gold distributions (KL 0.209 vs 1.442; Jev puts nearly all its mass on one option). It would rank fourth or fifth among the board's zero-shot rows, between Featherless Simple Jev (0.716) and prima-ratio (0.702). lev is 9 points under Jev, between OpenDecider-small and Bongard-mini, with a KL that still beats Jev. Both clear the Prior by a wide margin. The gold is a 4B-class teacher, so a model can score lower where the teacher is wrong; the comparison is against Jev on the same gold, not against truth. Per-question results are in the scratch JSON; both models are weakest on the 4-level `urgency` and `risk` scores of the agent-trace workflow (0.36 to 0.48) and strongest on the yes/no questions (0.76 to 0.96).

Latency: lev answers each question as a separate prompt, so a five-question case costs 2,464 input tokens on average and 0.58 s warm. Clef-Flash reads the state once for all five questions (868 tokens) and answers in 0.37 s warm, so it is both more accurate and faster on multi-question requests, at twice the VRAM. Neither measurement uses the 16k or 32k context the presets allow; the longest typed-decisions case was 4,740 tokens on lev.

### Apple Silicon memory estimate

No decision model was run on a Mac. Estimate with the doc-006 fit formula: GGUF weights + f16 KV cache at the context + 1 GB overhead. On Apple Silicon the whole figure must fit the Metal working-set ceiling, which llama.cpp reports as `recommendedMaxWorkingSetSize` at load (about two thirds to three quarters of unified memory). The reference machine here is an M3 Pro with 36 GB, ceiling about 27 GB.

| model | quant | weights | total @8k | total @32k | 36 GB Mac | 24 GB Mac | 16 GB Mac |
|---|---|---|---|---|---|---|---|
| Laya | Q8_0 | 0.4 GB | 2.5 GB | 5.5 GB | fits | fits | fits |
| lev | Q8_0 | 4.5 GB | 6.6 GB | 9.8 GB | fits | fits | fits at 8k |
| Kev-4B | Q8_0 | 4.5 GB | 6.6 GB | 9.8 GB | fits | fits | fits at 8k |
| Clef-Flash | Q8_0 | 9.7 GB | 11.7 GB | 15.0 GB | fits | fits at 8k | no |
| Clef-Flash | Q4_K_M | 6.5 GB | 8.6 GB | 11.8 GB | fits | fits | fits at 8k |
| Clef | Q4_K_M | 19.2 GB | 22.4 GB | 28.8 GB | fits at 8k | no | no |
| OpenJev | Q4_K_M | 19.0 GB | 22.1 GB | 28.6 GB | fits at 8k | no | no |

Latency on a Mac is not estimated; the OpenJev card reports its 4-bit MLX build answering on a Mac, and llmman reports 0.43 s warm for a Gemma 4 decision on an M4 Max, which bounds the order of magnitude for a 4B to 9B decoder at well under a second.

### Where each candidate falls short of Jev

Jev 1.13.0: 255 options, 2 to 10 levels, 64k per request and 32k for state plus the longest question, text only, every question answered independently against the same state, calibrated by training (RLCD), hosted, $0.042 per million input tokens, needs a key and a network.

| candidate | option limit | state length | temperatures | Score legend | joint vs independent | other gaps |
|---|---|---|---|---|---|---|
| lev Q8_0 | 255, but labels must be single tokens (A..ZZ) | no stated cap; 32k context set on saturn; 4,740-token typed-decisions cases fine | fitted per type and per option-count band, applied by the server; card warns calibration transfers less to unfamiliar task families | legend returned | independent; each question is its own prompt, so input tokens scale with question count (488 tokens for a 3-question README example, 2,464 mean for 5-question typed-decisions cases) | measured accuracy 0.637 vs Jev 0.727 on typed-decisions; weak on 5-level ratings and minimal-edit pairs (card) |
| Clef-Flash Q8_0 | 255 | 16k default; the whole prompt must fit one ubatch (16,384 on saturn), so a long state plus many questions fails rather than truncates | none in the header; the joint head's softmax is used raw ("not guaranteed to be calibrated") | legend returned | joint: all questions in one prompt and one pass, answers can depend on each other; the server serves only this endpoint while loaded | measured accuracy 0.707 vs Jev 0.727 on typed-decisions, with a better KL (0.209 vs 1.442); 9B at Q8_0 is 9.7 GB plus 1 GB mmproj |
| Clef Q4_K_M | 255 | same as Clef-Flash | none | legend returned | joint | 27B at Q4 is tight on the 3090 (22 GB at 8k); JevBench measured BF16, so a Q4 run is a quant mismatch; not installed |
| Kev-4B Q8_0 | 255; text only, no images | 65k served, 8k validated | one temperature for all types (2.41) | legend returned | independent | unmeasured on JevBench and typed-decisions for this generation; not installed |
| Laya Q8_0 | 255, but the head budget is 192 tokens for options plus question, so above about 20 options accuracy collapses (card: 0.425 on Banking77) | 512 tokens total by default, about 320 for the state; 8k ceiling | per type and bucket | legend returned | independent | 0.362 zero-shot on typed-decisions (card), I 1.8 on JevBench; a fixture, not a model to ship answers from |
| Julia-1 Q8_0 | 2 to 20 on the card | 8k combined, 48 tokens per option | none in the header | legend returned | independent | 73.15% typed-decisions claimed on its own card, unverified here; multilingual |
| OpenJev Q4_K_M | 52 per pass | 16k prompt | per type | legend returned | independent | CC-BY-NC-4.0; 27B tight at Q4 |
| Nimble Q8_0 | 52 | none stated | none in the header | legend returned | one prompt lists all questions | CC-BY-NC-4.0; Calibration 69.9 on JevBench |
| any chat model via NUMP-005 schema | schema enum, no practical limit | provider context | none: no probabilities at all | numpty would build it | one JSON object for all questions | no confidence; the only route for hosted chat providers |
| any GGUF chat model via llmman | 52-ish (letter labels, two-letter above 26) | model context | none; `x_label_mass` reports how much mass was on labels | returned | independent | separate daemon; uncalibrated |

## Fallback for chat models (AC #3)

The question: when no decision model is loaded, should numpty answer Choice, Score, and Noul questions with an ordinary chat model, and how.

Two routes exist.

1. Grammar plus logprobs on llama-server. Render the question as a prompt, constrain the answer to single-token labels with a GBNF grammar, ask for `n_probs`, read the label probabilities, renormalise. This is what discussion ggml-org/llama.cpp#29269 (NakliTechie, 2026-09-22, "Ideas") proposed as a native endpoint, with a working external wrapper (`llamacpp-jev`, MIT). The only maintainer-side reply (ericcurtin, 2026-10-01) says new APIs are hard to land in the server and points to llmman. Ten days later PR #29818 landed a native endpoint for models that carry decision metadata, not for arbitrary chat models. Issue #27174 (2026-08-16, closed stale 2026-10-01) records a related limit: `/v1/completions` with `echo: true` returns logprobs only for generated tokens, so prompt-position loglikelihood scoring does not work on llama-server. For this route it means one request per question with `max_tokens: 1`, and label probabilities taken from the top-`n_probs` list of the first sampled token; a label that falls outside that list is missing, and the mass the model put on non-label tokens is thrown away by the renormalisation. Checked on saturn with `gemma-4-31b-Q4` (2026-10-06, `nprobs_probe.py`): `/completion` with `n_predict: 1`, `n_probs: 10`, and a grammar `root ::= "A" | "B" | "C"` returns `completion_probabilities[0].top_logprobs` with pre-sampling logprobs, `A` at 0.0, `B` at -16.9, and `C` absent from the top 10; with `post_sampling_probs: true` only the sampled `A` at 1.0 remains. The mechanism works, the distribution is one-hot and uncalibrated, and a label can fall out of the list.
2. Structured output through NUMP-005. Compile the question set to the portable JSON Schema subset (doc-004: Choice to a string enum, Score to an integer enum, Noul to a boolean) and ask the chat model for one JSON object. Works on every NUMP-005 provider, not only llama.cpp. Returns a label per question, no probabilities and no confidence.

llmman (`github.com/llmmanorg/llmman`, from 0.1.497, 2026-09-30) is the third option and the one the maintainers pointed at: a local daemon that serves `POST /v1/systemone` for any GGUF with a chat template, with the same request and response shape plus an `x_label_mass` field per answer (how much probability the model put on the labels before renormalisation). It does not go through llama-server's HTTP API; it runs the model on libllama itself, because "llama-server ... will not tell you the probability of a token it was not asked to sample" and its earlier attempt through the HTTP API "could only approximate the numbers". Its own blog states the probabilities are the model's own and are not a calibrated chance of being right. `typesafe-sdk` with `base_url` works against it unchanged.

Verdict for numpty:

- Do not build route 1. Upstream chose a metadata-gated native endpoint over grammar emulation, the approximation is documented by the people who tried it, and a working implementation already exists behind the same wire contract (llmman). If a user wants decisions from a chat model, llmman is a `base_url`, not numpty code.
- Route 2 is a possible adapter in NUMP-007 (a decision model backed by a `Model` with a schema), honest about having no probabilities: `confidence` and `probabilities` absent, not fabricated. It is cheap because NUMP-005 exists, and it is the only route that works with the hosted providers. Whether to include it in NUMP-007's first slice is a NUMP-007 planning question; this spike only says it must not pretend to be calibrated, and the abstraction must allow answers without probabilities.
- Supporting the System One wire protocol makes the question moot for llama.cpp: a native decision model, llmman over a chat model, TypeSafe, and the other hosts all look the same to the client.

## Quyet-1.0-Large (verified 2026-10-05)

Candidate: `mradermacher/Quyet-1.0-Large-GGUF`, a quant of `chinhnc/Quyet-1.0-Large` (Gemma-4-31B-it fine-tune, Apache-2.0). Ranked first on JevBench v1.6.0 (Capability 81.7, Jev 1.13 is 76.5). Claimed public-test accuracy 0.909, hard ECE 0.089.

Result: not compatible as published. The GGUF header (Q4_K_M) has no `gemma4.decision.type`, no `tokenizer.chat_template.systemone`, and no temperature keys. llama-server returns 501 for it. mradermacher converted it as a plain `gemma4` chat model.

The mechanism does match the `openjev` type. From the `quyet` package source (`github.com/ncchinh/quyet`, `src/quyet/llm/`):

- One forward pass per question. Softmax over the logits of letters A..J at the last prompt token, divided by a per-type temperature. Nothing is generated.
- Temperatures (`quyet_config.json`): choice 1.3007, score 1.3159, noul 1.4957. Per type only, no option-count buckets.
- Limit of 10 options. noul renders A = true text, B = false text, which matches `openjev`'s true-first order.
- Prompt version 2, a single user turn with no system message and no closing line, rendered with the Gemma 4 chat template, `add_generation_prompt=True`, `enable_thinking=False`:

```
State:
{state or compact JSON}

Question: {instructions}
{one of:
 "Choose the option that fits best." |
 "Choose the level that fits best (levels are ordered from lowest to highest)." |
 "Choose A if the statement is true for this state, B if it is not."}

Options:
A. {text}
B. {text}
```

  Option text fallbacks: choice uses the label key when the description is empty, score uses the level index, noul uses "true" / "false".
- Gemma 4 turn markup, rendered on saturn with thinking disabled: `<|turn>user\n...<turn|>\n<|turn>model\n<|channel>thought\n<channel|>`.
- Letters A..Z and a tokenize to single tokens in the Gemma 4 vocabulary (verified on saturn with `/tokenize`).
- Quyet truncates the state to 6000 tokens and the prompt to 8000. llama.cpp's openjev path has no truncation, so the server context size must cover the prompt.

What a working GGUF needs: `gemma4.decision.type = "openjev"`, the three temperature keys, and a `systemone` jinja template that reproduces the prompt above with the Gemma 4 markup. The gguf-py scripts do not add arbitrary new keys (`gguf_set_metadata.py` only changes existing keys, `gguf_new_metadata.py` only knows general.*, chat template, and special tokens). A short gguf-py reader-to-writer copy script, or a converter change, is needed. This is unverified work. Two differences from Quyet's own output remain even then: llama.cpp computes `confidence` with the TypeSafe formulas, Quyet reports `p_max`. llama.cpp accepts up to 52 options, Quyet was trained with 10. Deferred: a 31B Q4 is tight on the 3090 at 8k context and does not fit at 32k (doc-006), and the recurrent doc-006 run watches for an upstream conversion.

## Decision

See decision-001. Short form: NUMP-007 targets the System One wire protocol, recommended client `typesafe-sdk` as an optional extra with final authority in NUMP-007; Clef-Flash Q8_0 is the recommended local model, lev Q8_0 the small alternative, Laya Q8_0 the offline test fixture; no grammar-and-logprob emulation in numpty; a NUMP-005 schema adapter without probabilities is allowed but scheduled by NUMP-007.

## Sources

- llama-server README, `tools/server/README.md`, section "POST /v1/systemone" (master, 2026-10-06); PR ggml-org/llama.cpp#29818; discussion #29269; issue #27174.
- TypeSafe: `docs.typesafe.ai/api`, `docs.typesafe.ai/models`, `typesafe-sdk` 0.7.2 source (`_core/endpoints.py`, `errors.py`, `response_types.py`, `config.py`).
- Model cards: `interfaze-ai/lev`, `Cloudflare/clef-flash`, `Cloudflare/clef`, `SupersonicLabs/Julia-1`, `convaiinnovations/laya`, `jaredpalmer/kev-4b`, `openjev/openjev`, `alibiserikbay/JevK5`, `Mapika/decider-4b-GGUF`, `Mapika/decider-2b-GGUF` (all read 2026-10-06), plus the ggml-org GGUF repos.
- Benchmarks: `LocalLLaMA/typed-decisions` README and `all/test` parquet (2026-10-01 revision); JevBench v1.6.0 through doc-006.
- llmman: `github.com/llmmanorg/llmman` README and the blog post "llmman now speaks System One" (2026-09-30).
- Probes (scratch, not committed): `sdk_probe.py` and `sdk_probe.json` (wire diff), `td_probe.py` with `td_lev-4b-Q8.json` and `td_clef-flash-9b-Q8.json` (typed-decisions), `nprobs_probe.py` (fallback route), session-2 README and image probes.
