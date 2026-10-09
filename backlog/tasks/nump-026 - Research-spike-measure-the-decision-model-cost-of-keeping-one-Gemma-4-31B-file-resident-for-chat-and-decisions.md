---
id: NUMP-026
title: >-
  Research spike: measure the decision-model cost of keeping one Gemma 4 31B
  file resident for chat and decisions
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 00:39'
updated_date: '2026-10-09 16:01'
labels:
  - research
  - decision-models
dependencies:
  - NUMP-022
  - NUMP-025
references:
  - scripts/eval/harness.py
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
    and chat plus structured output matches Quyet's accuracy but not its
    calibration
  - doc-009 - Quyet-1.0-Large to a llama.cpp decision GGUF (NUMP-022)
  - doc-008 - Decision model evaluation protocol
  - doc-004 - Structured output across providers and Jev
  - decision-003 - Quyet-1.0-Large (type openjev
  - Q4_K_M
  - >-
    32k) replaces Winnow for text accuracy and Clef-Flash for images and
    calibration; Clef-Flash stays for throughput and small VRAM
  - >-
    decision-004 - Clef-Flash keeps the image row; Quyet-1.0-Large with the
    mmproj is the image fallback when Quyet is resident; no Benchmark Heaven
    submission of the Quyet conversion until a variant beats Clef-Flash on the
    rebuilt preview set
type: spike
ordinal: 29000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The expected numpty workload mixes chat calls and decision calls. The best decision model (quyet-large-Q4, decision-003 and decision-004) is Gemma-4-31B-it plus a merged text-only LoRA, served with five openjev header keys that make llama-server read option-letter logits at the last prompt token (doc-009). At Q4_K_M it takes 21 GB, as does the chat preset gemma-4-31b-Q4, so the two never co-reside on the 3090 (--models-max 1) and every switch between a chat call and a decision call costs a 4 to 5 s load. One resident file that serves both roles would remove the switch. Two routes: (B) the stock gemma-4-31b-Q4 GGUF with the same five keys and Quyet's template becomes a decision model with no adaptation, and keeps its chat template, so the measurement isolates the LoRA's contribution on the same metrics as decision-003 (JevBench public 231, typed-decisions, doc-008 protocol); the header temperature is Quyet's, so the base model's Brier and ECE are a lower bound unless the temperature is fitted on a held-out split, while accuracy is unaffected. (A) the resident quyet-large-Q4 answering /v1/chat/completions, if llama-server still serves chat on a GGUF with decision metadata (unknown), with a small chat-quality probe against gemma-4-31b-Q4 because the LoRA trained with thinking off on decision data. (C) Gemma 4 chat plus structured output (JSON schema, verbalized probabilities) is the naive client route; B is an upper bound on it and it uses incomparable calibration, so it runs only if B is close and the metadata route is unwanted. Order: B, then A's feasibility check, then A's quality probe only if B shows a large gap. Decision expected: which file stays resident for a mixed workload, and the measured cost of that choice. Spike rule: conversion outputs and presets live on saturn under ~/Build/numpty-eval/ and /opt/llama; probe scripts stay in scratch; result files may go under scripts/eval/results/ when the harness runs them unchanged.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Doc records test B: a copy of the stock gemma-4-31b-Q4 GGUF with the openjev keys and Quyet's template, the rendered prompt checked equal to Quyet's on the verbose server, served as a router preset, and measured with the doc-008 harness on JevBench public (231) and typed-decisions (2,000 decisions): correct, Brier, ECE, ordinal MAE, KL, warm p50 and tokens, beside the quyet-large-Q4 and clef-flash-9b-Q8 rows of decision-003
- [x] #2 Doc states the temperature used for the base model, whether it was fitted on a held-out split or reused from Quyet, and the calibration figures for both choices when fitted
- [x] #3 Doc records test A feasibility: whether the quyet-large-Q4 preset answers /v1/chat/completions (and with which chat template and thinking setting), with the request and response recorded
- [x] #4 If test B shows a large gap, the doc records a chat-quality probe of quyet-large-Q4 against gemma-4-31b-Q4 on a small fixed set of numpty-style prompts, with the prompts and both answers, and a stated verdict; if the gap is small the doc says why the probe was skipped
- [x] #5 Doc states whether test C (chat plus structured output) was run and why, and if run, its accuracy on the same items with the caveat that its probabilities are verbalized
- [x] #6 Decision record names the resident file for a mixed chat-and-decision workload (stock Gemma 4 31B with decision keys, Quyet serving both roles, or two files with the switch cost), the measured accuracy and calibration cost of the choice, and the condition that reopens it
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 doc records reasoning and sources
- [x] #2 decision record produced
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Spike plan (2026-10-09, amended: test C runs either way). Nothing in the repo changes except scripts/eval/results/<preset>/ (harness unchanged), one doc and one decision. Probe scripts live in scratch and on saturn under ~/Build/numpty-eval/probes/nump-026/. models.ini backed up to .bak-2026-10-09 before any edit. Manual server on port 8099, stopped after each step. All requests sequential.

0. Sources. Quyet model card (huggingface.co/chinhnc/Quyet-1.0-Large) and github.com/ncchinh/quyet for any statement on generation or chat use and on what the LoRA loss covers (letter token only?); llama.cpp b11429 tools/server/server-decision.cpp and server.cpp for whether a decision-typed GGUF gates /v1/chat/completions; jevbench c6004e0 adapters (is there a chat-completions adapter with structured output, and how it maps verbalized probabilities) and doc-004 for the structured-output prompt and schema conventions. Quote what is found.

1. Verify yesterday's finding (test A, AC #3 and #4). Every request and response recorded (JSON) and summarized in the doc.
   a. Router reproduction. Four fixed prompts (chicken, 'The capital of France is', a numpty-style tool-selection question, a short JSON extraction), greedy (temperature 0), max_tokens 256, thinking off and on (chat_template_kwargs.enable_thinking), on quyet-large-Q4 and gemma-4-31b-Q4. Record finish_reason, completion tokens, first 200 chars.
   b. Conversion ruled out. Manual server on the unmodified Quyet-1.0-Large.Q4_K_M.gguf with the quyet-large-Q4 preset flags (ctx 32768, q8_0 KV, no draft), same prompts. Same degeneration expected: then the five keys and the systemone template are not the cause.
   c. Flags ruled out. Manual server on the chat file gemma-4-31B-it-qat-UD-Q4_K_XL.gguf with the same flags as 1b, same prompts. Healthy output expected.
   d. Quantified. llama-perplexity on a fixed public text (wikitext-2-raw test, first ~16k tokens, downloaded into a fresh dir on saturn, sha recorded) for the Quyet systemone file, the unmodified Quyet file and the Gemma chat file. Second-token probe: /completion with n_probs 10 on one decision prompt and one chat prompt, both models, showing the top-10 at the first and second generated positions (does the distribution collapse after the letter?).
   e. Optional, only if 1d is ambiguous (Quyet PPL within ~20% of Gemma): mradermacher Quyet Q8_0 (32.7 GB, partial offload, CPU RAM 62 GB) on the same text, to separate the LoRA from the Q4_K_M quant. Otherwise the doc states that the LoRA and the quant cannot be separated without bf16 and why that is acceptable.
   f. Doc verdict: AC #3 = the preset answers chat with the Gemma template, thinking off, output unusable; AC #4 = the chat-quality probe is closed by 1a-1d (broken, not degraded), with the evidence.

2. Test B build. gguf_add_decision.py (unchanged, doc-007) copies the chat preset's file gemma-4-31B-it-qat-UD-Q4_K_XL.gguf to gemma-4-31B-it-qat-UD-Q4_K_XL-systemone.gguf with the five keys (type openjev, Quyet's three temperatures, quyet_systemone.jinja). Preset gemma-4-31b-Q4-systemone = the gemma-4-31b-Q4 lines (128k ctx, q4_0 KV, MTP draft, sampling) plus jinja = true. Reload. Record GET /v1/models modalities for the new preset, one chat request (chicken, thinking on) to show it still chats, one TypeSafe decision request (README example) beside Quyet's answers. If the MTP draft breaks decision requests, drop model-draft from the preset and record it.
   Base-file choice (review item): (i) the chat preset's qat-UD-Q4_K_XL file, recommended: it is the file that would stay resident, so it answers the task's question directly; the LoRA isolation is approximate because Quyet's quant is mradermacher static Q4_K_M. (ii) download mradermacher's static Q4_K_M of gemma-4-31B-it (18.7 GB) as a same-quant base: clean isolation, not the resident file. Plan: (i), and (ii) only if the JevBench gap in step 4 is within 5 items, where quant noise could flip the reading.

3. Prompt parity (AC #1). compare_prompts.py and requests.json from probes/nump-022 against the verbose manual server on the new file: the 7 rendered prompts and token counts must equal replica.json.

4. Measure test B (AC #1). doc-008 commands td_score.py, td_samples.py, jevbench.py on gemma-4-31b-Q4-systemone; results to scripts/eval/results/gemma-4-31b-Q4-systemone/. Primary configuration = the chat preset settings, because that is how the resident file would run. If the JevBench gap to Quyet exceeds 5 items, re-run jevbench.py under the Quyet preset settings (32k, q8_0 KV, no draft) to separate the KV and draft effects from the LoRA. Table beside quyet-large-Q4 and clef-flash-9b-Q8: correct, Brier, ECE, ordinal MAE, td accuracy, KL, warm p50, tokens.

5. Temperature (AC #2). Scratch td_probs.py (harness functions) records per-decision probabilities for the new preset in one extra td run; jevbench predictions.jsonl already has them. Scratch fit_temp.py fits one T per type by NLL on the first 50 cases of each workflow using offline rescaling p' ∝ p^(T_quyet/T') (exact, since the server computes softmax(logit/T)), and reports Brier and ECE at Quyet's T and at the fitted T on the other 50 cases and on JevBench (second check: fit on easy+original, score hard). Accuracy is unchanged by T. Doc reports both.

6. Test C (AC #5), run either way: the baseline for models that cannot be converted (cloud Sonnet, Luna), measured on the same items with the same scorers, so that even 'no change against test B' is recorded as signal.
   a. Route: the unmodified gemma-4-31b-Q4 chat preset, POST /v1/chat/completions, response_format json_schema (grammar-constrained), thinking off. One question per request (as Quyet and JevBench do), so the prompt is one user turn carrying the same content as the systemone prompt (state, question line, lettered options) plus the instruction to return {"probabilities": {"A": p, ...}} over the given letters, summing to 1. Prompt text and schema recorded verbatim in the doc so a later task can send the same thing to cloud models. Sampling: temperature 0, max_tokens bounded. Invalid or unparseable JSON counts as a uniform answer and is counted (schema validity column).
   b. Scratch chat_decide.py turns a systemone request into that chat request and the reply into a systemone-shaped answer (normalized probabilities, choice/score/noul answer by the doc-008 rules), reusing harness functions. jevbench: its own chat/structured adapter if step 0 finds one that renders the same prompt, else a scratch adapter around chat_decide.py; td: a scratch wrapper that feeds chat_decide.py answers to the td_score.py scorer unchanged.
   c. Sets: JevBench public (231) and typed-decisions (2,000 decisions), full. Optional third row, JevBench only, thinking on, if the run fits in the session (231 generations with thought on a 31B model; stop and record if it passes 1 h).
   d. Columns: the same as test B (correct, Brier, ECE, ordinal MAE, td accuracy, KL, Brier, mean p_max, td ECE) plus output tokens per decision, p50 and p95 latency, schema validity, and a sharpness note (verbalized probabilities cluster on round numbers). Caveat in every table: the probabilities are verbalized, not logit-derived, so the calibration columns are not comparable with B and Quyet in mechanism, only in outcome.
   e. Results: the tables in the doc and the raw JSON on saturn under probes/nump-026/test-c/ and in scratch. Not under scripts/eval/results/, because the harness does not run this route unchanged. A follow-up task to promote chat_decide.py into scripts/eval/ (so cloud models get the same three commands) is created from the doc if the user wants it; this spike commits no script.

7. Thresholds for the decision (AC #6), fixed before measuring. Three candidates for the mixed workload: the stock chat file with decision keys (B), the stock chat file with structured output (C), two files with the switch (Quyet for decisions). Quyet-for-both is ruled out by step 1. B stays resident if it is within 5 JevBench items and 0.02 td accuracy of Quyet and its fitted-T calibration is within 0.01 Brier of Quyet's; C is named only if it matches B within the same margins and the metadata route is unwanted; otherwise two files with the measured 4-5 s switch. The decision records the cost of each route against Quyet, and C's figures as the reference row for unconvertible models. Reopen conditions: a Quyet release that chats, a decision-only workload, a larger GPU, a numpty measurement of the switch frequency, or a cloud model measured on the C route.

8. Deliverables: doc-011 (sections per AC, test C prompt and schema, sources, probe file list), decision-005, results dir for B, saturn memory update. Time: about 4 h of saturn time (three doc-008 runs 10 min, test C full sets 1 to 2 h at 31B generation, perplexity 3 files ~15 min, probes, copy 10 s). Run in a new session.

Review decision (user, 2026-10-09): test B base file = the chat preset's gemma-4-31B-it-qat-UD-Q4_K_XL.gguf, option (i) in step 2. Option (ii), the same-quant static Q4_K_M download, is dropped; the doc notes the quant difference against Quyet's mradermacher Q4_K_M as a caveat on LoRA isolation, nothing more.

Review decision revised (user, 2026-10-09): the step 2 conditional stands as first written. Test B base = the chat preset's gemma-4-31B-it-qat-UD-Q4_K_XL.gguf. If test B lands within 5 JevBench items of quyet-large-Q4, download mradermacher's static Q4_K_M of gemma-4-31B-it (18.7 GB), convert it the same way as a second preset, run jevbench.py on it, and report it as the same-quant base so the gap is attributed to the LoRA, not the quant. The earlier appended note dropping option (ii) is superseded.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Finding before planning (user, 2026-10-09): POST /v1/chat/completions on quyet-large-Q4 ("Why did the chicken cross the road?", max_tokens 1000, default sampling) returned degenerate text: '---\n1. **1.01** {0_0} {1_0} {1_0} ...' to the token limit; prompt_tokens 24, so the Gemma chat template rendered normally. The conversion writes the decision template to tokenizer.chat_template.systemone and leaves tokenizer.chat_template untouched (doc-009, gguf_add_decision.py), so the template is not the cause. Test A feasibility (AC #3) is therefore the endpoint answering, but the quality looks broken by the LoRA; test B (one metadata-modified stock Gemma 4 31B for both roles) becomes the primary route, conditional on a small JevBench gap and the file still chatting normally.

Probes 2026-10-09 (router, from the Mac): quyet-large-Q4 chat at temperature 0 gives the same degeneration ('---\n1. **1.0_1_1_1...'); /completion with no template, 'The capital of France is', greedy: ' Paris.' then '1. **1.1**\n1.2\n1.1...'; a decision-shaped chat prompt (invoice over the limit, A yes / B no, 'answer with the letter only') gives 'A' then '{12,400_10,000} {1' junk. gemma-4-31b-Q4 control on the chicken prompt: healthy (thinking in reasoning_content, then a normal answer, finish stop, 313 tokens). Reading: the LoRA trained the first answer token only and broke generation after it; not sampling, not the template. Test A quality probe (AC #4) can be closed from this evidence; test A feasibility (AC #3) is 'answers, unusable'. For test B, also check with one chat request that the metadata-modified stock file still chats (the systemone template is a separate key, so it should).

Step 1a (2026-10-09, router, greedy, max_tokens 256, chat_probe.py in scratch): quyet-large-Q4 with enable_thinking=false answers all four prompts normally (chicken 163 tok stop, 'Paris', run_tests() first, correct JSON extraction), indistinguishable in kind from gemma-4-31b-Q4. With enable_thinking=true Quyet degenerates ('---\n1. **1.0_0_0...' to the limit) on three of four prompts (the JSON extraction survived behind a '---' prefix), reasoning_content empty. gemma-4-31b-Q4 healthy in both modes. Reading: yesterday's degeneration was the thinking channel (llama-server defaults thinking on for Gemma 4); the LoRA trained with thinking off and broke generation inside the thought block only. Consequence: Quyet-for-both (thinking off) is a live candidate again; step 7's 'ruled out by step 1' no longer holds, and the AC #4 chat-quality probe runs regardless of test B's gap. Steps 1b-1d continue as planned to quantify the LoRA's generation damage.

Steps 1b-1c (manual server 8099, Quyet preset flags, same four prompts): the unmodified Quyet-1.0-Large.Q4_K_M.gguf gives byte-identical answers to the converted preset (healthy with thinking off, '---\n1. **1.0_0...' with thinking on), so the five keys and the systemone template are not the cause; the chat file gemma-4-31B-it-qat-UD-Q4_K_XL.gguf under the same flags is healthy in both modes. Second-token probe (/completion, n_probs 10, greedy): on the decision prompt Quyet's top token is 'A' at p 0.037 (Gemma: 'A' 0.56, 'The' 0.41); after the empty thought block Quyet's first chat token 'The' has p 0.001 (Gemma 0.88), while positions 2-4 are sharp on both (0.60/0.96/0.89 vs 0.99/1.00/0.98); with the thought block open Quyet puts 0.02 on '---' and 0.001 on '<|channel>' (Gemma 1.00 on '<|channel>'). Reading: the LoRA flattened the distribution at the readout position (the only position it trained) and destroyed the thought-open token; greedy decoding recovers normal text, sampling at the chat preset's temperature 1.0 would draw the first token from a flat top-40. Step 1d perplexity (wikitext-2 test, ctx 2048 x 8): Quyet systemone 1325, Quyet unmodified 1325 (identical, tensors unchanged), Gemma chat file 1133: both implausibly high for raw text, diagnostics running before the figure is used. Step 2 build done: gemma-4-31B-it-qat-UD-Q4_K_XL-systemone.gguf (17.29 GB, 7 s copy).

Step 1d perplexity is unusable on this build: llama-perplexity b11429 gives PPL 1133 to 3196 for the stock Gemma 4 31B chat file on wikitext-2 and on War and Peace at every setting tried (ctx 512/2048, fa on/off, batch 512/2048), so the tool is broken for Gemma 4 here, not the models; the Quyet vs Gemma ratio (1325 vs 1133 at the same setting) is reported with that caveat only. Replacement for the quantified generation check: the second-token probe (step 1b-1c) plus a first-token flatness probe across the AC #4 prompts. Step 3 parity: the test B file rendered all 7 nump-022 requests byte-equal to replica.json (full log compared after the server flushed; the live comparison lags one request as in doc-009) and input_tokens equal (203/184/87/91). Step 2 preset gemma-4-31b-Q4-systemone added (chat preset lines plus jinja = true, 128k ctx, q4_0 KV, MTP draft), GET /v1/models reports output_modalities ['decisions'] and input ['text']; README example answers cancel 0.9998, urgent 0.986, mood calm 0.9993 (Quyet: 0.9966, 0.721, 0.770/0.219/0.011); chat on the same preset still thinks and answers (finish length at 200, reasoning_content present); 23.0 GB VRAM with the draft.

Test B measured (results/gemma-4-31b-Q4-systemone/, chat preset settings, MTP draft kept: the smoke run showed decisions work with it): JevBench 179/231 (Quyet 208, Clef-Flash 190, Winnow 198), Brier 0.301, ECE 0.045, ordinal MAE 0.195, paraphrase agreement 31/36 (Quyet 35); typed-decisions acc 0.674 (Quyet 0.804, Clef-Flash 0.707), KL 0.455, Brier 0.173, pmax 0.711, ECE 0.046; warm p50 1.43 s, tokens 1479 (equal to Quyet, same prompt). Families that lose most: multi_hop 9/18 (Quyet 15), probability 5/10 (10), intent 20/24 (24), long_policy 9/19 (13), routing 9/12 (12). Gap 29 items, so the same-quant base download is not triggered and the 32k/q8_0/no-draft re-run is queued. AC #4 chat probe (8 numpty-style prompts, chat_quality.json): Quyet greedy thinking-off answers all 8 and is right on 6, with first-token artifacts ('//1. git_diff' as a tool name, 'errorslyly') and a wrong date count (policy); at the [*] temp 0.2 the tool_pick prompt loops to 1024 tokens; at the chat preset sampling (temp 1.0) three of eight are corrupted ('median(15)', 'Priyaed', a 1024-token loop). Gemma greedy thinking-off: all 8 clean (policy wrong by reasoning, right with thinking on). Verdict: Quyet is not a chat model; usable only greedy, with artifacts, no thinking. AC #2 temperature: fit_temp.py (offline rescale, exact) on the first 50 cases per workflow, scored on the other 50: noul T 1.50->2.10 (KL to gold 0.221->0.131, Brier 0.116->0.087, ECE 0.053->0.038), choice 1.30->2.56 (KL 0.69->0.46, Brier 0.217->0.187, ECE 0.075->0.130), score 1.32->1.54 (KL 0.41->0.35, Brier 0.165->0.150); applying the td-fitted T to JevBench makes Brier worse on noul (0.158->0.175) and choice (0.383->0.401): the two sets pull in opposite directions (teacher spread vs one-hot labels), JevBench fit splits are too small (36/72/12 items) and overfit. Stored results keep Quyet's T.

Test C JevBench (jevbench openai_compat adapter, the board's cloud route, strict json_schema through the router on the unmodified gemma-4-31b-Q4 chat preset, temperature 0, thinking off, run dir data/runs/jevbench-gemma-4-31b-Q4-nothink): 209/231 (Quyet 208, test B 179, Clef-Flash 190), macro 0.919, Brier 0.199, ECE 0.109, ordinal MAE 0.283, schema validity 1.0, paraphrase 34/36, p50 1.05 s / p95 3.44 s (Quyet 0.27 / 2.40), 58 output tokens and 702 input tokens per item. Verbalized distributions: 216 of 231 items at pmax 1.0, 13 distinct pmax values, 97.6 percent of values on the 0.05 grid, so the probabilities are labels with a few hedges and the ECE is the 22 wrong items at p 1.0. Per family equals Quyet everywhere except adequacy 11 (12), long_policy 14 (13), tradeoff 6 (5); C-only correct 8, Quyet-only 7, both wrong 15. Reading: the base model's instruction following with a schema beats the base model's letter readout on Quyet's prompt by 30 items and matches Quyet on accuracy; what the LoRA buys over this route is calibration (Brier 0.139 vs 0.199) and 4x latency. Plan step 7 thresholds: C passes the 5-item JevBench margin and fails the 0.01 Brier margin. typed-decisions on the C route is running (2,000 chat completions).

Test C typed-decisions (chat_decide.py, same prompt and schema as the JevBench row, one chat completion per question, thinking off, test-c/td_chat_nothink.json): accuracy 0.729 (Quyet 0.804, test B 0.674, Clef-Flash 0.707, Jev 1.13 board 0.727), KL 0.851, Brier 0.181, mean pmax 0.818, ECE 0.089; noul 0.842 / choice 0.695 / score 0.670; schema validity 2000/2000, all finish stop, 47 output tokens per decision, 390 input tokens; p50 1.00 s per question, p95 1.37 s, so about 5 s per five-question case against Quyet's 1.57 s and test B's 1.43 s. Verbalized: 95.9 percent of values on the 0.05 grid, 318 of 2000 at pmax 1.0, 17 distinct pmax values. Beats test B on 16 of 20 questions and loses to Quyet on 17 of 20; weakest agent_trace action 0.41 and urgency 0.49. Thresholds: C fails the 0.02 accuracy margin (gap 0.075) and the 0.01 Brier margin on both sets. Decision stays two files.

Test B under Quyet's settings (preset gemma-4-31b-Q4-systemone-32k: 32k, q8_0 KV, no draft; results/gemma-4-31b-Q4-systemone-32k/jevbench.json): 180/231, Brier 0.294, ECE 0.047: the KV type and the draft are not the gap. Test C thinking on (JevBench only, data/runs/jevbench-gemma-4-31b-Q4-think): 227/231, every item that produced JSON correct, paraphrase 36/36, long_policy 17/19, temporal_numeric 13/15; 4 failures (2 long_policy, 2 temporal_numeric) still thinking at the 4,096-token limit, counted wrong; Brier 0.009, ECE 0.015 (labels, 215 of 227 at p 1.0); 567 output tokens mean, p50 3.86 s, mean 7.1 s, p95 25 s. typed-decisions on that route not run (about 3 h). First-token probe (first_token.py, 8 AC #4 prompts, thinking off): Quyet's top first token 0.000 to 0.055 vs chat preset 0.58 to 1.00; Quyet sharp again from token 2. doc-008 gained the two test B rows and the presets. doc-011 and decision-005 (body written into the file below the frontmatter, CLI has no body option) written. tests/test_eval.py 18 passed. Saturn probes synced to ~/Build/numpty-eval/probes/nump-026/. Thinking-on JevBench row started late because macOS has no timeout(1); rerun with a perl alarm.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-10-09 13:17
---
Plan ready for review
---

author: @claude
created: 2026-10-09 13:57
---
Plan amended: test C runs unconditionally as the baseline row for unconvertible (cloud) models; prompt and schema recorded for reuse. Ready for review.
---

author: @claude
created: 2026-10-09 14:02
---
Base file for test B settled: chat preset QAT Q4_K_XL. No open review items; awaiting approval to move to In Progress in a new session.
---

author: @claude
created: 2026-10-09 14:05
---
Base-file conditional restored: QAT Q4_K_XL default, same-quant static Q4_K_M only if B is within 5 JevBench items of Quyet. Ready for approval.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Decision-005: two files with the switch. Quyet stays the decision model, the chat preset the chat model. Evidence (doc-011, doc-008 harness unchanged, saturn router, 2026-10-09): test A, Quyet chats only greedy with thinking off (LoRA flattened the readout position: top first token 0.000 to 0.055 vs 0.58 to 1.00 for Gemma, thought-open token gone), artifacts in 1 of 4 replies, corrupt under the chat preset's sampling, unmodified GGUF identical so the conversion is not the cause. Test B, the chat file plus the Quyet openjev keys (prompt parity 7/7 byte-equal): JevBench 179/231 (180 at Quyet's 32k/q8_0 settings) vs Quyet 208, typed-decisions 0.674 vs 0.804, results in scripts/eval/results/gemma-4-31b-Q4-systemone[-32k]/; temperature fitted on a held-out half helps typed-decisions KL by a third and hurts JevBench Brier, Quyet's T kept. Test C, chat plus json_schema with the jevbench openai_compat prompt (board cloud route): thinking off 209/231 and td 0.729, verbalized label-like probabilities (Brier 0.199/0.181), 1 s per question; thinking on 227/231 (4 token-limit failures), 3.9 s median, 25 s p95, td not run. No one-file route meets the pre-set margins on both sets. Verified by the three doc-008 commands (tests/test_eval.py 18 passed), jevbench summaries, and the recorded probe JSON on saturn ~/Build/numpty-eval/probes/nump-026/. Repo changes: two results directories, doc-011, doc-008 rows, decision-005 (body written into the file; the CLI has no body option). Not committed.
<!-- SECTION:FINAL_SUMMARY:END -->
