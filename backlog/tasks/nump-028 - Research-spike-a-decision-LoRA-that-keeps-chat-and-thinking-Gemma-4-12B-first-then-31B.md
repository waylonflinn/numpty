---
id: NUMP-028
title: >-
  Research spike: a decision LoRA that keeps chat and thinking, Gemma 4 12B
  first, then 31B
status: To Do
assignee: []
created_date: '2026-10-09 16:41'
labels:
  - research
  - decision-models
dependencies:
  - NUMP-026
references:
  - 'https://huggingface.co/datasets/LocalLLaMA/typed-decisions'
  - 'https://huggingface.co/chinhnc/Quyet-1.0-Large'
documentation:
  - >-
    doc-011 - One Gemma 4 31B file for chat and decisions: stock Gemma with
    decision keys
  - Quyet for both roles
  - and structured output (NUMP-026)
  - >-
    decision-005 - Two files with the switch: Quyet stays the decision model and
    the chat preset the chat model; stock Gemma 4 31B with decision keys loses
    29 JevBench items
  - >-
    and chat plus structured output matches Quyets accuracy but not its
    calibration
  - doc-009 - Quyet-1.0-Large to a llama.cpp decision GGUF (NUMP-022)
  - doc-007 - Winnow-12B to a llama.cpp decision GGUF (NUMP-018)
  - doc-008 - Decision model evaluation protocol
type: spike
ordinal: 31000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
NUMP-026 (doc-011, decision-005) showed that Quyet-1.0-Large, a Gemma-4-31B-it LoRA, lost chat because its loss touched one position: the letter readout after the empty thought block. At that position the next-token distribution went flat (top token 0.000 to 0.055 against 0.58 to 1.00 for the base) and the thought-open token disappeared, so thinking-on generation and sampled chat degenerate while greedy thinking-off chat survives with artifacts. That is a loss and data choice, not a property of decision LoRAs. The same work found the headroom: the stock 31B with thinking on and a JSON schema answers 227 of 231 JevBench public items (Quyet 208 at Q4) at 14x the latency, and its thinking-off verbalized route gives 209 with label-like probabilities. The user intends to train their own Jev-like models and serve them on llama.cpp without a fork (type openjev, metadata-only conversion, doc-007 and doc-009). The question of this spike: can one LoRA on a Gemma 4 instruct model keep chat and thinking at base quality and beat Quyet on JevBench accuracy and typed-decisions calibration, and what is the plan to prove it on Gemma 4 12B on the 3090 (Winnow-12B, 198/231, is the bar there) before a 31B run on a rented H100. Candidate ingredients to weigh, not decide here: replay of thinking-on and thinking-off chat sequences, a KL-to-base term on the non-letter logits at the readout position, soft labels from typed-decisions train (exists on the Hub, same format, 4B-class teacher) and from self-distillation (label numpty-shaped questions with the 31B thinking-on structured-output route, average several samples), training with a proper scoring loss so the temperatures are not a post-hoc fit, QLoRA on the 3090 for 12B, the effect of a merged LoRA on the MTP draft acceptance rate. JevBench public and typed-decisions test stay held out. Deliverables: a Backlog doc and a decision record (go or no-go, and the 12B-first plan with its budget). Spike rule: probes and labeling runs stay in scratch and on saturn under ~/Build/numpty-eval/; nothing outside Backlog docs and decisions is committed.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Doc states which training signal the LoRA uses and where it comes from: typed-decisions train, self-distilled labels from the 31B thinking-on structured-output route, or both, with the label format (hard or soft), the volume, the generation cost on saturn, and the contamination check against JevBench public and typed-decisions test
- [ ] #2 Doc states the loss and the chat-preservation mechanism (replay mix, KL-to-base at the readout position, or another), with the evidence from doc-011 for why it addresses the Quyet failure, and the pass criterion for chat and thinking after training (the doc-011 chat probe, the first-token and second-token probes, and a thinking-on check)
- [ ] #3 Doc states the training stack and budget for Gemma 4 12B on the 3090 (QLoRA or other, rank, sequence length, batch, memory, wall time) and for 31B on a rented GPU, with sources
- [ ] #4 Doc states the serving path for the trained model (merge, GGUF, type openjev conversion with the trained template and temperatures, mmproj and MTP draft consequences) and confirms it needs no llama.cpp fork
- [ ] #5 Doc states the evaluation plan: doc-008 commands for decisions, the chat probe and thinking check for chat, the Winnow-12B (198) and Quyet (208, 0.804) bars, and what result at 12B justifies the 31B run
- [ ] #6 Decision record states go or no-go for the 12B run, the chosen signal, loss and stack, the budget, and the condition that reopens it
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 doc records reasoning and sources
- [ ] #2 decision record produced
<!-- DOD:END -->
