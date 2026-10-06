---
id: NUMP-016
title: 'Research spike: local Jev-like decision models for llama.cpp'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-05 21:00'
updated_date: '2026-10-06 15:27'
labels:
  - research
dependencies: []
references:
  - doc-004
  - 'https://docs.typesafe.ai/introduction/quickstart'
  - 'https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md'
  - 'https://benchmarkheaven.com/jev-models'
  - 'https://huggingface.co/blog/ggml-org/decision-models-in-llamacpp'
  - 'https://github.com/ggml-org/llama.cpp/pull/29818'
  - 'https://github.com/ggml-org/llama.cpp/discussions/29269'
  - 'https://docs.typesafe.ai/api'
  - 'https://madewithjev.com/open-source-jev'
  - 'https://huggingface.co/datasets/LocalLLaMA/typed-decisions'
  - 'https://github.com/allebee/jevk5'
  - 'https://github.com/Mapika/decider'
  - decision-001
  - doc-006
documentation:
  - doc-005 - Local decision models for llama.cpp (NUMP-016)
type: spike
ordinal: 16000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Jev (TypeSafe) is a hosted, paid, API-key-gated structured decision model: Choice, Score, and Noul questions answered with a predicted value, confidence, and a probability distribution (see doc-004). numpty already runs a local Qwen through llama.cpp via OpenAIChat (NUMP-004), and NUMP-007 will add a decision-model abstraction for Jev. Before designing that abstraction we need to know whether a local, offline model can fill the same role: a Jev-like backend for users without a TypeSafe key, an offline test double, and a check that the abstraction is not shaped around one vendor. Emphasis is on models and techniques that run under llama.cpp (GGUF, llama-server), because that is the local runtime numpty already supports. Candidate directions include small instruct LLMs with grammar-constrained output plus token logprobs for label probabilities, reranker or classifier-style models that llama-server can serve, and NLI-style zero-shot classifiers (which may not be llama.cpp-compatible and should be noted as such). Deliverables are a Backlog doc and a decision record; no code.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Doc catalogs the native decision models llama.cpp 0.6.0+ serves at /v1/systemone (ggml-org GGUFs: Julia-1, Laya, Kev-4B, lev, OpenJev, Clef; plus other GGUF-available System One models such as JevK5 and decider) with base model, size, question types, option and state-length limits, license, and published JevBench / typed-decisions scores
- [x] #2 Doc records how closely llama-server's /v1/systemone matches TypeSafe's wire contract (request, response, errors, model and auth handling) and whether one client (typesafe-sdk with base_url, or a stdlib HTTP client) can target both
- [x] #3 Doc records the fallback for non-decision chat models (grammar plus n_probs logprobs, or NUMP-005 structured output without probabilities), llama.cpp's stance on it (discussion #29269, issue #27174), and whether numpty should support it
- [x] #4 Doc compares candidates on accuracy and calibration, VRAM and latency measured on the deployment target saturn (RTX 3090, 24 GB; lev-4b-Q8 and clef-flash-9b-Q8 installed), an Apple Silicon memory estimate from the doc-006 fit formula, and license, and names where each falls short of Jev (option limits, state length, uncalibrated temperatures, Score legend, joint vs independent answering)
- [x] #5 Decision record states which local model(s) numpty should support first for NUMP-007, and whether NUMP-007's abstraction targets the System One wire protocol rather than the TypeSafe SDK
- [x] #6 No code or files outside Backlog docs and decisions are committed; probe scripts stay in scratch
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 doc records reasoning and sources
- [x] #2 decision record produced
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Scouting result (2026-10-05)

- llama.cpp v0.6.0 (PR #29818, merged 2026-10-02) adds a native TypeSafe-compatible POST /v1/systemone. Decision models are marked by GGUF metadata ({arch}.decision.type); GET /v1/models reports output_modalities ["decisions"]. Non-decision models return 501. Six ggml-org GGUFs: Julia-1 (144M mmBERT), Laya (421M ModernBERT), Kev-4B (Qwen3.5-4B-Base), lev (4B), OpenJev (27B, vision), Clef (27B, joint answering, systemone-only).
- Earlier proposal (discussion #29269) to emulate via grammar + n_probs was declined; llmman did it externally. So the logprob route is a fallback, not the main path.
- Other GGUF-available System One models: JevK5 (Qwen3.5-4B LoRA, Apache-2.0, JevBench 62.0 vs Jev 63.3), decider-2b/4b (Qwen3.5, Apache-2.0, llama-cpp-python + own /v1/systemone server), opendecider-small (Qwen3-4B). Encoder-only (Von, Laya) are faster but shorter state limits (512-8k tokens).
- Benchmarks: JevBench (benchmarkheaven.com, 4 axes), typed-decisions (HF, 5,387 items, proper scoring rule). Jev 1.13 ~81.7 on typed-decisions.
- Local machine: llama-server 0.5.0 build 11146 (Homebrew). Needs 0.6.0 for probing /v1/systemone.

## Plan

1. Wire contract: diff llama-server /v1/systemone README against docs.typesafe.ai/api and doc-004 SDK notes. Probe: point typesafe-sdk base_url at local llama-server; record what breaks (auth header, model field, error shapes). Requires brew upgrade llama.cpp to 0.6.0 (ask before upgrading).
2. Catalog: one table of native models (ggml-org six) and GGUF-available others. Fields per AC #1. Pull sizes and limits from HF model cards and README.
3. Quality: collect published JevBench and typed-decisions scores; note what is author-claimed. Run a small sanity probe (10-20 questions from typed-decisions) against Kev-4B and Laya locally for latency and memory on this Mac. No full benchmark.
4. Fallback: summarize #29269 / #27174 and the NUMP-005 schema route; recommend keep or drop.
5. Write doc; write decision record (model to support first; protocol-vs-SDK target for NUMP-007).

Decision expected: yes. Sources: refs on task.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Session 1 (2026-10-05) — resume here

Done:
- Plan approved, task In Progress. doc-005 created and linked; it holds all verified findings (saturn URL, build, 501 behavior, decision types table, Quyet analysis).
- Verified on saturn (https://saturn.wayforwardlabs.com, build b11429): /v1/systemone exists, returns 501 for text models, Gemma 4 single letters are single tokens, Gemma 4 turn markup captured.
- Verified Quyet-1.0-Large-GGUF (mradermacher) is NOT a llama.cpp decision model as published (no gemma4.decision.type, no systemone template). Mechanism matches the openjev type. Patch requirements recorded in doc-005.
- Read GGUF headers of ggml-org Kev-4B and OpenJev (decision keys, temperatures, full OpenJev systemone template is in scratch output, summarized in doc).

Constraints: saturn handles one request at a time. Probe scripts are in the session scratch dir only (gguf_kv.py reads GGUF KV via HTTP Range). Nothing committed outside Backlog.

Next (maps to plan steps 1-5):
1. Wire diff: fetch docs.typesafe.ai/api, compare to llama-server README section (scratch/server-README.md lines 1698-1835) and doc-004 SDK notes. Probe typesafe-sdk base_url=https://saturn.wayforwardlabs.com once a decision model is installed. Record in doc AC #2.
2. Ask the user to add a decision model to saturn models.ini (suggest ggml-org/Kev-4B-GGUF Q8_0, Apache-2.0, 4.5 GB; OpenJev is CC-BY-NC). Then run a 10-20 item probe from HF LocalLLaMA/typed-decisions, sequentially. Record latency and sanity accuracy. AC #1, #4.
3. Fill the catalog rows for Julia-1, lev, Clef from their HF cards (sizes, limits, licenses). Add JevBench / typed-decisions scores where published. AC #1, #4.
4. Fallback verdict (grammar+n_probs vs NUMP-005 schema). AC #3.
5. Decision record: first model to support, and protocol-vs-SDK target for NUMP-007. Quyet patch: recommend defer unless a native conversion appears. AC #5.

## Session 2 (2026-10-06): decision models installed on saturn (plan step 2)

- Presets added to /opt/llama/config/models.ini (backup models.ini.bak-2026-10-06), picked up with `GET /v1/models?reload=1`, no restart: `lev-4b-Q8` (lev-Q8_0.gguf, ctx 32768) and `clef-flash-9b-Q8` (Clef-Flash-Q8_0.gguf, ctx/batch/ubatch 8192; clef evaluates the whole prompt in one ubatch). Both files verified against HF sha256. Router advertises output_modalities ["decisions"] for both before load.
- README example probe (choice+noul+score) via the router: lev cold 2.0 s incl. load, warm 0.18 s, 5.7 GB VRAM, 488 input tokens; clef-flash cold 3.2 s, warm 0.25 s, 10.7 GB VRAM, 324 input tokens. Both pick `billing`; lev score 1.59, clef 2.21; noul 0.56 vs 0.42. Logs confirm `decision model type: lev` / `clef` (clef enables embedding mode).
- Not installed: Kev-4B Q8_0 (doc-006 try, 4.5 GB) and Laya Q8_0 (test double, 0.4 GB); awaiting go-ahead to download. Pre-existing warning on saturn: `failed to mlock ... Cannot allocate memory` (load-mode = mlock in [*], memlock ulimit), not caused by these presets.
- Next: typed-decisions 10-20 item probe against lev then clef-flash (sequential), wire diff with typesafe-sdk base_url (plan step 1), AC #1/#4 rows.

- 2026-10-06 later: `clef-flash-9b-Q8` now multimodal. Added mmproj-Clef-Flash-BF16.gguf (0.92 GB, sha256 verified) and raised ctx/batch/ubatch to 16384; router shows input_modalities [text, image]. Synthetic probe (256px red square / blue circle, 3 questions incl. a noul): color and shape at 0.98, has_text 0.003; 372 input tokens per image request, warm 0.34 s, cold 3.7 s, 13.9 GB VRAM. Text-only probe unchanged. Server warns Qwen-VL wants >=1024 image tokens for grounding and suggests --image-min-tokens 1024; not set (small images only).

- AC #4 amended 2026-10-06: memory/latency now measured on saturn (RTX 3090), Apple Silicon reduced to an estimate from the doc-006 fit formula. Work resumes in a new context: wire diff (step 1), typed-decisions probe (step 2), fallback verdict (step 4), decision record (step 5).

## Session 3 (2026-10-06): wire diff, typed-decisions runs, fallback, decision

- Wire diff (AC #2): typesafe-sdk 0.7.2 with base_url=saturn, dummy api_key, model=lev-4b-Q8 answers system_one unchanged (cold 2.0 s, warm 0.23 s). Differences: 400 not 422 for validation, 501 for non-decision model (SDK maps to TypeSafeInternalServerError), output_tokens 0, no request id, models.list() fails (OpenAI list shape). Field tables in doc-005.
- typed-decisions (AC #4): ran the full test split (400 cases, 2,000 decisions, five questions per request) on saturn instead of the planned 10-20 items; it cost about 4 min per model. Scorer's uniform baseline reproduces the board's KL 0.444 and Brier 0.238. clef-flash-9b-Q8: acc 0.707, KL 0.209, Brier 0.110, warm p50 0.37 s, 13.5 GB. lev-4b-Q8: acc 0.637, KL 0.297, Brier 0.165, warm p50 0.58 s, 5.7 GB. Jev 1.13.0 board row: 0.727 / 1.442 / 0.148.
- Fallback (AC #3): #29269 unanswered by maintainers except a pointer to llmman; #27174 closed stale. Grammar+n_probs verified mechanically on gemma-4-31b-Q4 (top_logprobs: A 0.0, B -16.9, C absent from top 10). Verdict in doc-005: no emulation in numpty; NUMP-005 schema adapter allowed without probabilities; llmman is a base_url.
- Catalog (AC #1): decider GGUFs have no decision metadata (headers read), JevK5 has no GGUF. Option and state limits and claimed scores per model from the cards. Apple Silicon estimate from the doc-006 formula (M3 Pro 36 GB reference).
- doc-005 rewritten in full. decision-001 created (status proposed, awaiting human acceptance). The backlog CLI has no decision body command, so the body below the frontmatter was written directly; frontmatter untouched.
- Probe scripts (sdk_probe.py, td_probe.py, nprobs_probe.py) and result JSONs stay in session scratch; nothing committed outside Backlog.

2026-10-06 review: user chose typesafe-sdk as the recommended client (optional extra, placeholder key for local hosts, same pattern as OpenAIChat), final authority with NUMP-007. decision-001 point 1 and doc-005 verdict amended; stdlib client dropped from the recommendation.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-10-05 21:19
---
Plan ready for review
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Research complete. doc-005 holds the full catalog (8 ggml-org native GGUFs plus the non-native JevK5, decider, Quyet, Winnow, OpenSourceJev rows with limits, licenses, JevBench and typed-decisions scores), a field-by-field wire diff of llama-server /v1/systemone against TypeSafe's API and typesafe-sdk 0.7.2 (verified by pointing the SDK at saturn), full typed-decisions test-split runs on saturn for clef-flash-9b-Q8 (acc 0.707, KL 0.209) and lev-4b-Q8 (acc 0.637, KL 0.297) against Jev's board row (0.727, 1.442), VRAM and latency on the RTX 3090, an Apple Silicon estimate, a per-candidate shortfall table, and the fallback verdict (no grammar+n_probs emulation; NUMP-005 schema adapter allowed without probabilities; llmman as a base_url). decision-001 (proposed): NUMP-007 targets the System One wire protocol with a stdlib client; Clef-Flash Q8_0 recommended, lev Q8_0 as the small alternative, Laya as the offline fixture. Verified with probe scripts in scratch (sdk_probe, td_probe with a baseline that reproduces the board's uniform KL and Brier, nprobs_probe); nothing committed outside Backlog docs and decisions.
<!-- SECTION:FINAL_SUMMARY:END -->
