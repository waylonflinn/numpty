---
id: NUMP-016.01
title: >-
  Recurrent research: cross-reference ggml-org decision models with JevBench
  scores and RTX 3090 fit
status: Done
assignee:
  - '@claude'
created_date: '2026-10-05 22:22'
updated_date: '2026-10-06 15:27'
labels:
  - research
  - recurrent
dependencies: []
references:
  - 'https://benchmarkheaven.com/api/jevbench/v1.6.0'
  - 'https://huggingface.co/EldanRing/Winnow-12B'
documentation:
  - 'doc-006 - Decision model watch: ggml-org GGUFs vs JevBench'
parent_task_id: NUMP-016
type: spike
ordinal: 17000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
llama.cpp 0.6.0 serves GGUF decision models at `/v1/systemone`. The ggml-org Hugging Face collection "Decision models" (8 repos as of 2026-10-05: Clef, Clef-Flash, OpenJev, Laya, Julia-1, Kev-4B, lev, Bespoke-Nimble-9B-v3) is the set numpty can run locally without conversion work. doc-005 catalogs six of them with sizes and licenses but no benchmark scores, and names JevBench (benchmarkheaven.com/jev-models, v1.6.0, 92 ranked systems) as the public benchmark. Picking a first model for NUMP-007 needs the two lists joined: which collection models are measured on JevBench, under what name and version, and how they score against Jev 1.13.0 and against the non-native candidates (Quyet, JevK5, decider). Name matching is not trivial: the board lists "kev 4B", "kev 8B", "Clef", "Clef-Flash", "OpenJev", "Laya", "Laya multilingual", "lev", "Bespoke Nimble 9B", and it is not obvious which ggml-org GGUF each row corresponds to (version, quant, base model).

Deployment target is saturn, a LAN machine with one RTX 3090 (24 GB VRAM). Each model needs a fit assessment: which quants fit in VRAM with a usable context, and which do not.

This task is recurrent. The feature launched in llama.cpp on 2026-10-02 and new models are expected daily. Each run refreshes the catalog, re-pulls the JevBench board, and adds a dated header to the doc with a brief analysis of the available models, their tradeoffs, and a recommendation on each. The task itself does not make the NUMP-007 decision; that stays in NUMP-016 AC #5. A Gemma 4 31B variant with a compatible GGUF (Quyet-1.0-Large, deck-31B, or similar) is the watch item: when one appears it is likely to change the recommendation.

Deliverable is a new Backlog doc, separate from doc-005, that grows one dated section per run.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A new Backlog doc exists with one row per model in the ggml-org decision-models collection: HF repo, decision type, base model, parameter count, GGUF quants with file sizes, license
- [x] #2 Each row names the matching JevBench system (or states "not measured") with the evidence for the match: linked project source, base model, version string; version or quant mismatches between the GGUF and the measured system are noted
- [x] #3 Each matched row records JevBench Intelligence, Calibration, Speed, Cost, Capability, official Composite and rank, cost per 1k decisions, median latency, and Jev-class eligibility, with Jev 1.13.0 as the reference row
- [x] #4 Each row states whether a quant fits the RTX 3090 (24 GB): quant, weight size, estimated KV cache at the stated context, verdict (fits / tight / no)
- [x] #5 Doc states the JevBench release, pool size, and date, and links the aggregate results JSON and its SHA-256
- [x] #6 Doc lists JevBench systems with no GGUF in the collection that are watch items (Gemma 4 31B variants first), with their scores, so a new compatible GGUF can be spotted
- [x] #7 Each run adds a dated header to the doc with: what changed since the last run (new models, new JevBench release, score moves), a brief tradeoff analysis of the available models, and a recommendation per model (adopt / try / skip) with reasons
- [x] #8 The refresh procedure is written down in the doc so a later run repeats the same steps and the same sources
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 doc records reasoning and sources
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Sources (all machine-readable, verified 2026-10-05)

- HF collection: `GET https://huggingface.co/api/collections/ggml-org/decision-models` -> items[].id, lastModified. Per repo: `GET https://huggingface.co/api/models/<repo>?blobs=true` -> cardData.license, cardData.base_model, siblings[].rfilename + size. GGUF header KV (decision.type, temperatures, context length, n_layer, n_head_kv, head size) via the existing scratch `gguf_kv.py` (HTTP Range read, no download).
- JevBench: `GET https://benchmarkheaven.com/api/jevbench/<release>` (v1.6.0 today). SHA-256 matches the page (b8560f6e...). Per system: key, display, author, repo, underlying, licence, gpu, class, model_pin, rank, ranks, jevbench_score, capability, axes{I,C,S,K}, cost.usd_per_1000, speed.p50_s_adjusted, last_measured_on, listing. `not_measured[]` carries key, repo, reason. Jev-class eligibility derives from cost <= 2x and p50 <= 2x Jev 1.13.0 row.
- Fit: RTX 3090 = 24 GB. VRAM = GGUF file size + KV cache (2 * n_layer * n_head_kv * head_dim * ctx * 2 bytes f16) + ~1 GB overhead; mmproj excluded (text only). Context for the estimate: 8k (the Quyet prompt cap) and 32k. Verdict: fits (< 20 GB), tight (20-23 GB), no (> 23 GB).

## Procedure (one run; written into the doc as the refresh section)

1. Pull collection + per-repo metadata. Diff repo list and lastModified against the previous dated section.
2. Pull JevBench JSON for the current release; record release, sample counts, source_sha256, scored date. Diff against previous release/version.
3. Match each collection repo to a JevBench system by: base_model (HF) vs underlying/repo (JevBench), then name, then author. Record evidence and mismatch notes (quant, version, BF16 vs Q8, "thinking" variants, measured-on-text).
4. Fill the catalog table (AC #1-#4). One row per repo; one fit line per quant.
5. Watch list (AC #6): JevBench ranked + not_measured systems with no collection GGUF, ordered Gemma 4 31B first, then Gemma 4 12B, then other open weights with repo links. Include score, licence, repo.
6. Dated section (AC #7): changes since last run; tradeoffs (capability vs VRAM vs licence vs latency vs option limits from doc-005); per-model adopt / try / skip.

## Doc layout

New doc "Decision model watch: ggml-org GGUFs vs JevBench" (type other). Fixed sections at top (Sources and procedure, Fit method), then one dated section per run, newest first. Each dated section: Catalog table, Watch list, Analysis and recommendations. doc-005 keeps the protocol and mechanism detail; this doc links to it, does not repeat it.

## Scratch tooling

One throwaway script `jev_xref.py` in scratch: pulls both sources, emits the catalog and watch tables as Markdown for pasting into `backlog doc update`. Not committed (spike rule). If the task recurs more than twice, propose promoting it to a tracked script in a follow-up task.

## Out of scope

No decision record (NUMP-016 AC #5). No model installs or probes on saturn. No GGUF conversion.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Run 1 (2026-10-05)

- Script `scripts/jev_xref.py` (uncommitted by request, stdlib only). Reads HF collection API, per-repo API with blobs, GGUF header KV via HTTP Range (stops before tokenizer arrays, so chat templates are not read), JevBench aggregate JSON. Hand-maintained MATCHES table carries the evidence; WATCH_KEYS lists watch rows.
- doc-006 created: fixed sections (sources + procedure, fit method) then "Run 2026-10-05".
- Findings: JevBench v1.6.0 JSON hash matches the page. 3 clean matches (lev #14, Clef-Flash #21, Clef #43), Nimble #33 matched with version caveat, Laya #84 matched; OpenJev, Julia-1, Kev-4B (this Qwen3.5 generation) unmeasured. The board "OpenJev" is razorback16 on diffusiongemma, not the ggml-org GGUF. The board "kev 4B" is the Qwen3 predecessor.
- Winnow-12B (rank 6, Gemma 4 12B, Apache) ships a Q8_0 GGUF but its header has no gemma4.decision.type; it needs the author llama.cpp fork. Top watch item.
- 31B at Q4_K_M is ~19 GB: tight on the 3090 at 8k, no at 32k. Gemma 4 12B rows are the realistic 3090 target.
- Recommendations: adopt lev Q8_0; try Clef-Flash Q8_0 and Kev-4B Q8_0; Clef Q4_K_M later; Laya as test double; skip OpenJev, Nimble, Julia-1.

Next run: rerun the script with the current release, diff against this section, add a new dated section above it.

Recurrence: reopen this task per run (user decision 2026-10-05). Each run: set To Do -> Planning (confirm sources/release) -> In Progress, rerun scripts/jev_xref.py, add a dated section to doc-006 above the previous one, uncheck/recheck ACs, update final summary, set Done.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-10-05 22:42
---
Plan ready for review
---

author: @claude
created: 2026-10-05 23:17
---
Run 1 done. Recurrent task: leaving In Progress pending guidance on how runs should be tracked (reopen per run, or one subtask per run).
---

author: @claude
created: 2026-10-06 00:06
---
Run 1 closed. Reopen per run.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Run 1 complete (2026-10-05). doc-006 "Decision model watch: ggml-org GGUFs vs JevBench" created with fixed sections (sources + refresh procedure, RTX 3090 fit method) and a dated section "Run 2026-10-05" holding the catalog (8 repos), matched JevBench v1.6.0 scores with Jev 1.13.0 as reference, match evidence per repo, per-quant fit table at 8k and 32k context, GGUF header facts, watch list (Gemma 4 31B first), and adopt/try/skip recommendations. Verified: JevBench JSON SHA-256 equals the hash on the page; GGUF headers read from HF for all 8 repos plus Winnow-12B; tables generated by scripts/jev_xref.py (uncommitted). Recommendation: adopt lev Q8_0, try Clef-Flash Q8_0 and Kev-4B Q8_0, Clef Q4_K_M later; Winnow-12B is the top watch item (Q8 GGUF exists, no upstream decision metadata). Task is recurrent: next run reruns the script, diffs, and adds a new dated section.
<!-- SECTION:FINAL_SUMMARY:END -->
