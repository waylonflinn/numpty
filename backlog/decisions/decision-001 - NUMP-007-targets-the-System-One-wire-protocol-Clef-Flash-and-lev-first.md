---
id: decision-001
title: NUMP-007 targets the System One wire protocol; Clef-Flash and lev first
date: '2026-10-06 12:51'
status: accepted
---
## Context

NUMP-007 adds a structured decision model (Choice, Score, Noul with probabilities and confidence) to numpty. Jev (TypeSafe) is hosted and key-gated. NUMP-016 asked whether a local, offline model can fill the same role and what NUMP-007's abstraction should target. Evidence is in doc-005 (protocol, catalog, measurements, fallback) and doc-006 (JevBench cross-reference, RTX 3090 fit).

What the research established:

- llama.cpp v0.6.0 serves GGUF decision models at `POST /v1/systemone` with TypeSafe's request and response shape. `typesafe-sdk` 0.7.2 with `base_url` pointed at saturn works unchanged for `system_one`; only `models.list()` and the error status codes (400 instead of 422, 501 for a non-decision model) differ.
- The same wire shape is served by TypeSafe, llama-server, llmman (any GGUF chat model), meraGPT, Liquid AI, and the independent JevK5 and decider servers. It is the de facto protocol, not a vendor SDK.
- Of the eight ggml-org GGUFs, lev (4B, Apache-2.0, 4.5 GB) and Clef-Flash (9B, Apache-2.0, 9.7 GB) are measured on JevBench, fit the RTX 3090 and a 24 GB Mac with room, and answered the full typed-decisions test split on saturn: Clef-Flash accuracy 0.707, KL 0.209, Brier 0.110, 0.37 s warm, 13.5 GB with mmproj; lev accuracy 0.637, KL 0.297, Brier 0.165, 0.58 s warm, 5.7 GB. Jev 1.13.0 on the same board: accuracy 0.727, KL 1.442, Brier 0.148.
- Grammar-and-logprob emulation for chat models was not adopted upstream and is approximate; llmman already provides it behind the same wire shape.

## Decision

1. NUMP-007's abstraction targets the System One wire protocol (`POST /v1/systemone`: `state`, `model`, `questions`; `answers`, `model`, `usage`). A backend is a base URL plus a model name plus a key. TypeSafe is one such backend, llama-server and llmman are others; none gets a vendor-specific code path for the request or answer shape. Recommended client: `typesafe-sdk` as an optional extra (`numpty[typesafe]`), the same pattern as `numpty[openai]` and `numpty[anthropic]`; local hosts take a placeholder key, as `OpenAIChat(..., api_key="none")` already does for llama-server. Final authority on SDK versus stdlib client rests with NUMP-007 planning.
2. The client tolerates the documented differences: 400 and 422 both mean a bad request, 501 means the model is not a decision model, `output_tokens` may be 0, a request id may be absent, and option limits are model-specific (52 for openjev and nimble types). Model discovery is not part of the protocol; numpty does not call `GET /v1/models` through the decision client.
3. Local models numpty supports first, in this order: Clef-Flash Q8_0 (`ggml-org/Clef-Flash-GGUF`, `clef-flash-9b-Q8` on saturn) as the recommended local model: within 2 points of Jev on typed-decisions accuracy with better calibration, reads the state once for all questions, images supported. lev Q8_0 (`ggml-org/lev-GGUF`, `lev-4b-Q8`) as the small alternative: 4.5 GB, independent per-question answers, 255 single-token options, fits a 16 GB Mac. Caveats carried by the abstraction, not hidden: the clef type answers jointly and locks llama-server to this endpoint while loaded; its whole prompt must fit one ubatch; lev's input tokens scale with the question count.
4. Laya Q8_0 (0.4 GB, Apache-2.0, milliseconds on CPU) is the offline test fixture for NUMP-007's integration tests, not a model to recommend for answers.
5. Numpty does not implement grammar-and-logprob decisions over chat models. A chat-model adapter through NUMP-005 structured output (labels without probabilities) is allowed in the abstraction, must report that it has no probabilities, and is scheduled by NUMP-007 planning, not by this decision.
6. Quyet-1.0-Large and Winnow-12B (Gemma 4) are not pursued until an upstream-compatible GGUF with `decision.type` metadata exists. The recurrent doc-006 run watches for it.

## Consequences

- NUMP-007 can be tested end to end against saturn (`lev-4b-Q8`, `clef-flash-9b-Q8`) and offline against Laya without a TypeSafe key. A TypeSafe key exercises the same code path.
- The abstraction must allow answers without `probabilities` and `confidence`, and must not require `models.list()` (it fails against llama-server's OpenAI-shaped list).
- If the SDK is adopted: pydantic, httpx2, and tenacity enter the extra, not core; the SDK's exception classes stay behind numpty's own error type (it maps llama-server's 400 to `TypeSafeBadRequestError` and 501 to `TypeSafeInternalServerError`).
- Option-count and state-length limits are per model and must be surfaced as a backend property or an error, not assumed from Jev's limits.
- A later Gemma 4 decision GGUF (about 10 Capability points above lev and Clef-Flash on JevBench) changes the recommended model, not the protocol.
