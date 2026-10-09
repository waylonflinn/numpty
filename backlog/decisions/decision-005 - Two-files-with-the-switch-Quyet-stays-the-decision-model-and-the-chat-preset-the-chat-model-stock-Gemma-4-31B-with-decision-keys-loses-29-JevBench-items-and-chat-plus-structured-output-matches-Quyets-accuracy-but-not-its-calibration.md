---
id: decision-005
title: >-
  Two files with the switch: Quyet stays the decision model and the chat preset
  the chat model; stock Gemma 4 31B with decision keys loses 29 JevBench items,
  and chat plus structured output matches Quyet's accuracy but not its
  calibration
date: '2026-10-09 15:28'
status: proposed
---
## Context

NUMP-026 asked which Gemma 4 31B file stays resident on the 3090 for a workload that mixes chat calls and decision calls, and what that choice costs. The decision model `quyet-large-Q4` (decision-003, decision-004) and the chat preset `gemma-4-31b-Q4` are both 21 to 23 GB, the router keeps one model (`--models-max 1`), and every role change costs a 4 to 5 s load. doc-011 holds the measurements, doc-008 the protocol. Thresholds were fixed before measuring (NUMP-026 plan step 7): the stock file with decision keys stays resident if it is within 5 JevBench items and 0.02 typed-decisions accuracy of Quyet and its fitted-temperature calibration is within 0.01 Brier of Quyet's. The structured-output route is named only if it matches that within the same margins and the metadata route is unwanted. Otherwise two files with the switch.

Measured on saturn, RTX 3090, through the router, from the Mac, 2026-10-09:

| candidate for the resident file | JevBench correct / 231 | JevBench Brier / ECE | typed-decisions accuracy | typed-decisions KL / Brier to the teacher | decision latency | chat | switch |
|---|---|---|---|---|---|---|---|
| Quyet for both roles (`quyet-large-Q4`, chat with thinking off, greedy) | 208 | 0.139 / 0.043 | 0.804 | 0.270 / 0.111 | 0.27 s per question | greedy only: artifacts in 1 of 4 replies, corrupt at the chat preset's sampling, no thinking | none |
| stock Gemma with decision keys (`gemma-4-31b-Q4-systemone`, test B) | 179 | 0.301 / 0.045 | 0.674 | 0.455 / 0.173 | 0.29 s per question | the chat preset, unchanged | none |
| stock Gemma, chat plus JSON schema (`gemma-4-31b-Q4`, test C, thinking off) | 209 | 0.199 / 0.109 (verbalized) | 0.729 | 0.851 / 0.181 (verbalized) | 1.05 s per question, p95 3.4 s | the chat preset, unchanged | none |
| stock Gemma, chat plus JSON schema, thinking on (test C, JevBench only) | 227 (4 items ran out of the 4,096-token budget) | 0.009 / 0.015 (verbalized) | not run | not run | 3.9 s median, 25 s p95, 43 s max per question | the chat preset, unchanged | none |
| two files: Quyet for decisions, the chat preset for chat | 208 | 0.139 / 0.043 | 0.804 | 0.270 / 0.111 | 0.27 s per question | the chat preset, unchanged | 4.6 s to load Quyet, 4 to 5 s to load the chat preset, at every role change |

Findings behind the table (doc-011):

- Quyet's LoRA trained one position. At the readout position the next-token distribution is flat (top token 0.1 to 4 percent of the mass against 56 to 88 percent for the base model) and the thought-open token is gone. Greedy decoding recovers normal text; sampling does not. The unmodified Quyet GGUF behaves the same, so the conversion is not the cause.
- The LoRA is worth 29 JevBench items and 13 points of typed-decisions accuracy over the same base model on the same prompt with the same readout (test B). No temperature closes that gap, and the typed-decisions and JevBench sets want opposite temperature changes.
- The base model answers better by generating a JSON distribution than by letter readout on Quyet's prompt: 209 against 179 on JevBench. With thinking on it answers 227 of 231, every item that finished, at 14 times Quyet's latency; typed-decisions on that route was not run (about 3 h). The verbalized probabilities are labels with a few hedges (216 of 231 items at p 1.0, 97.6 percent of values on the 0.05 grid), so the Brier is 0.060 above Quyet's and the ECE 0.066 above, and each question costs a generation (1.05 s against 0.27 s).

## Decision

1. Two files. `quyet-large-Q4` stays the decision model and `gemma-4-31b-Q4` the chat model, as in decision-003 and decision-004. A mixed workload pays the switch: 4.6 s to load Quyet, 4 to 5 s to load the chat preset. Quyet for both roles is rejected for the chat role. The stock file with decision keys is rejected: 29 items and 13 points below Quyet, outside every margin.
2. The structured-output route (test C) is the named route when the chat file must stay resident and when a model cannot be converted (cloud models). With thinking off its measured cost against Quyet is: equal JevBench accuracy (209 against 208), 7.5 points less on typed-decisions (0.729 against 0.804), Brier 0.199 against 0.139 with label-like probabilities, and 4 times the latency per question. It fails the 0.02 accuracy and 0.01 Brier margins, so it does not replace Quyet. With thinking on it is the accuracy ceiling measured here (227 of 231 on JevBench, Brier 0.009) at 3.9 s median and 25 s p95 per question, and its typed-decisions figure is unmeasured. It is the route when accuracy outranks latency. The prompt and schema are in doc-011 so a cloud model can be measured the same way.
3. The test B preset `gemma-4-31b-Q4-systemone` and its 32k twin stay in `models.ini` as measured reference presets. They are not recommended for use.
4. The chat-template setting for any Quyet chat call, if one is ever made, is `enable_thinking: false` with temperature 0. Any other setting degenerates.

## Consequences

- numpty docs keep Quyet as the local decision model and the chat preset as the chat model, and state the switch cost for interleaved calls. A client that interleaves one decision per chat turn pays about 9 s per turn in loads; a client that batches decisions between chat turns pays it once per batch.
- The resident file for a numpty session is the one the next call needs. If a measurement of the real switch frequency shows loads dominating, the test C route on the resident chat file is the fallback with the costs in item 2.
- doc-006's watch gains: a Quyet release whose adaptation keeps generation (a chat-capable decision LoRA), and a cloud model measured on the test C route with the doc-011 prompt.
- Reopen when any of these holds: typed-decisions measured on the thinking-on structured-output route at or above Quyet's 0.804 (then the resident chat file serves decisions for workloads that accept about 4 s per question, and Quyet stays for the fast path); a Quyet or other Gemma 4 decision release that chats normally with thinking on; a decision-only workload (then decision-003 applies alone); a GPU that holds both files (48 GB); a numpty measurement of the switch frequency; a cloud model measured on the test C route; a calibration method for verbalized probabilities that brings test C within 0.01 Brier of Quyet.
- Follow-up candidates (not created): run typed-decisions on the thinking-on structured-output route (about 3 h on saturn, `chat_decide.py --thinking`); promote `chat_decide.py` into `scripts/eval/` so cloud models get the same three commands; measure the switch frequency in a numpty session.
