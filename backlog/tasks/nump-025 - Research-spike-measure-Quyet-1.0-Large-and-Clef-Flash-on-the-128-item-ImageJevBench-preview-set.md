---
id: NUMP-025
title: >-
  Research spike: measure Quyet-1.0-Large and Clef-Flash on the 128-item
  ImageJevBench preview set
status: Done
assignee:
  - '@claude'
created_date: '2026-10-08 21:44'
updated_date: '2026-10-09 00:15'
labels:
  - research
  - decision-models
dependencies:
  - NUMP-022
references:
  - >-
    https://github.com/fstandhartinger/model-market-comparison/tree/9f20f1e47991b005aa1811b6be435a7f32b4f2cf/data/raw/benchmarks/jevbench/multimodal-preview/source
  - 'https://benchmarkheaven.com/image-jev-bench'
  - >-
    https://github.com/fstandhartinger/jevbench/tree/bb05a33/results/imagejevbench/v0.1.3
  - 'https://huggingface.co/datasets/user9000/CLEVR-HOPE'
  - 'https://huggingface.co/datasets/hiyouga/geometry3k'
  - 'https://huggingface.co/datasets/mm-eval/ArxivQA'
  - 'https://huggingface.co/datasets/bevaya/FinQA'
  - 'https://huggingface.co/datasets/bevaya/ScreenSpot'
  - 'https://huggingface.co/datasets/osunlp/Multimodal-Mind2Web'
documentation:
  - >-
    doc-010 - ImageJevBench preview set rebuilt: Quyet-1.0-Large and Clef-Flash
    (NUMP-025)
  - >-
    decision-004 - Clef-Flash keeps the image row; Quyet-1.0-Large with the
    mmproj is the image fallback when Quyet is resident; no Benchmark Heaven
    submission of the Quyet conversion until a variant beats Clef-Flash on the
    rebuilt preview set
  - doc-009 - Quyet-1.0-Large to a llama.cpp decision GGUF (NUMP-022)
  - decision-003 - Quyet-1.0-Large (type openjev
  - Q4_K_M
  - >-
    32k) replaces Winnow for text accuracy and Clef-Flash for images and
    calibration; Clef-Flash stays for throughput and small VRAM
  - doc-008 - Decision model evaluation protocol
type: spike
ordinal: 28000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
decision-003 gives Quyet-1.0-Large (preset quyet-large-Q4, Gemma 4 mmproj) the image row of the requirement-to-model table on one synthetic probe (doc-009 AC #6: a red disc, seven questions, answered like Clef-Flash). Quyet never trained on images, so that row is provisional and the table says so. The ImageJevBench board (benchmarkheaven.com/image-jev-bench, v0.3.0, 2,441 items, 300 public / 1,200 sealed) does not publish its items and does not list Quyet; Clef-Flash is on it at Capability 52.2 (Intelligence 37.3, Calibration 67.2), Clef at 58.1. The jevbench repository ships only aggregate image results. The only item-level image set in the open is the September 2026 private preview round in fstandhartinger/model-market-comparison, data/raw/benchmarks/jevbench/multimodal-preview/source/ at commit 9f20f1e (2026-09-21): items-extended-real.json (128 choice items with rubric, gold, licence, source dataset and source row) and RUN-RESULT.md (the six systems measured on them: Luna 59.4%, Gemini 3.1 Flash-Lite 57.0%, djev-dev 47.7%, AlexWortega/openjev 4B v2 46.9%, decider-2b-vision 43.0%, reflex 4B 43.0% on all 128; 62.5% to 77.5% on the 80 image-reasoning items). The image files are not in the repository. The 60 CLEVR-HOPE, Geometry3K and ArxivQA items use the source image and question verbatim and can be rebuilt from the Hugging Face source rows. The 20 FinQA items need the source table rendered as an image with deterministic distractors, the 36 ScreenSpot items need five click markers drawn from the labelled bbox, and the 12 Multimodal-Mind2Web items need boxed and labelled candidates; the procedures are described in the transformation field but the code is not shipped, so those 68 are rebuildable only approximately. The 8 synthetic items (Z-Image-Turbo generations) are out of scope. Scope: rebuild what can be rebuilt with equal gold, run it against quyet-large-Q4 and clef-flash-9b-Q8 through the saturn router with data-URL images and a text-only control, record per-dataset and overall figures, and settle the image row. Not in scope: a Benchmark Heaven submission (the board measures self-hosted systems itself; state the condition for one), the v0.3 item pool, and new llama.cpp work. Spike rule: the dataset builder, the rebuilt images and the runner stay outside the repo (scratch and saturn); results go in the doc. If the set proves useful, promoting the runner into scripts/eval/ and storing results under scripts/eval/results/ is a follow-up chore, not this task. Decision expected: confirm or revise the image row of decision-003.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Doc states, per source dataset, whether the preview items can be rebuilt from the pinned item list and the Hugging Face source rows with the same gold, how (verbatim row, table rendering, marker drawing), which items were run, and a manifest (item id, source row, image sha256) kept with the rebuilt set
- [x] #2 Both quyet-large-Q4 and clef-flash-9b-Q8 answer the rebuilt items through the router with the image as a data URL, one request per item, doc-008 settings (sequential, no retries), and the doc records per-dataset and overall accuracy, Brier and ECE against the one-hot gold, p50 latency and mean input tokens
- [x] #3 A text-only control (same items without the image) is recorded for both models, so the doc can state how much of each model's accuracy comes from the image
- [x] #4 Doc compares the results with the preview-round figures in RUN-RESULT.md (per subset: image reasoning 80, computer and browser use 48) and with Clef-Flash's ImageJevBench v0.3 board row, and states what is and is not comparable (rebuilt approximations, quantization, a different item pool on the board)
- [x] #5 Decision record confirms or revises the image row of decision-003 (Quyet with the mmproj, Clef-Flash, or conditional on the image family) and states the condition under which a Benchmark Heaven submission of the Quyet conversion is worth it
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 doc records reasoning and sources
- [x] #2 decision record produced
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Spike plan (2026-10-08). Questions = AC #1-#5 as written; decision in scope (decision-004: image row of decision-003). Nothing enters the repo except doc-010 and decision-004; builder, images and runner live in the session scratch and, durably, on saturn under ~/Build/imagejev-preview/.

1. Sources, pinned. items-extended-real.json and RUN-RESULT.md at model-market-comparison 9f20f1e (sha256 recorded in the doc). Per-item preview results exist for all 128 items: results-gemini*.json, results-luna*.json (pred per item), results-openjev-real.log (ok/miss per item); use them for a per-item comparison, not only the aggregate table. Board page benchmarkheaven.com/image-jev-bench fetched 2026-10-08 (v0.3.0, built 2026-10-07): Clef-Flash Capability 52.2, Intelligence 37.3, Calibration 67.2, public set 130/235 = 0.553, ECE 0.189; also a "Winnow-12B (Q8_0 + F16 vision projector)" row at 50.0 (I 38.6, public 138/235, ECE 0.161): the board already measures an image-untrained Gemma 4 LoRA with the stock projector, the same construction as Quyet + mmproj. jevbench results/imagejevbench/v0.1.3 is aggregate only (Imajev-4B row); cite for the method, no item data.

2. Rebuild (builder script, Mac scratch, uv inline deps: pillow). Source rows verified today against the Hugging Face datasets-server: row 0 of Geometry3K test, ArxivQA train, FinQA test, ScreenSpot test, Mind2Web test_task equals the item's question/label; CLEVR-HOPE is config HOP00, split test_complex_ood, idx = source_row (rows 1, 11, 36 checked). Record the dataset revision the server reports. Per dataset:
   - CLEVR-HOPE 20, Geometry3K 20, ArxivQA 20: image and question verbatim, criteria from the item list, assert gold text equals the source answer. Exact rebuild.
   - FinQA 20: criteria (distractors) are in the item list; only the image is rebuilt: render table_ori with Pillow (fixed font, one row per line), assert gold option text equals exe_ans/answer (two items are yes/no). Approximate image, exact gold.
   - ScreenSpot 36: assert file_name and bbox equal source_label; draw five lettered markers; the gold letter from the item list centred on the bbox; four distractors from a deterministic rule (seed = item id, points outside the bbox, minimum spacing), recorded in the doc. Approximate.
   - Mind2Web 12: assert action_uid and positive backend_node_id; boxes from bounding_box_rect of the positive and the first four negatives with a non-degenerate rect; letters as in the item list; crop to a viewport-sized window containing all five boxes (rule recorded). Approximate.
   - Manifest items.jsonl: id, dataset, config/split/row, HF revision, kind (verbatim / rendered / markers / boxes), image sha256, check status. Copied with the images to saturn ~/Build/imagejev-preview/.

3. Run (runner script, scratch). Per item one POST /v1/systemone through the router (doc-008: sequential, no retries, latency from the Mac): state = the item's state without the image path, images = [data URL], one choice question with the rubric verbatim. Four passes: quyet-large-Q4 and clef-flash-9b-Q8, each with image and text-only control (512 requests, about 15-20 min). Smoke one item per model first to confirm the images field and the mmproj path. Raw responses kept.

4. Score (runner). Accuracy per dataset, per preview subset (image reasoning 80; computer and browser use 48), overall; Brier and ECE against the one-hot gold with the harness formulas; p50 latency; mean input tokens; chance per dataset; per-item agreement with openjev 4B, Gemini, Luna; image-minus-text delta per model.

5. Write doc-010 (sections: sources and pins, rebuild table AC #1, manifest, results AC #2 and #3, comparison AC #4 with the comparability caveats: rebuilt approximations on 68 items, Q4_K_M/Q8_0 against BF16, an unknown prompt wrapper in the preview round, a different and larger item pool on the board), then decision-004 (AC #5): confirm or revise the image row, and the Benchmark Heaven condition (expected shape: Quyet beats Clef-Flash on the rebuilt set by more than the 128-item noise band, and the board can measure the saturn preset or a public GGUF plus mmproj; read the Submit-a-model page during the spike). Link doc-010 and decision-004 on the task.

Review points: (a) not adding Winnow + a Gemma-4-12B mmproj as a third system despite the board row (out of AC scope; note it for the doc-006 watch); (b) marker, distractor and crop rules are ours, so the 68 approximate items compare to the preview round only loosely; (c) durable home of the rebuilt set is saturn ~/Build/imagejev-preview/, not the repo.

Amendment after review (2026-10-08, approved): (a) no Winnow + mmproj run; (b) approximate rules accepted; (c) replaces the saturn location above. Step 0, before the spike work: tidy ~/Build on saturn into ~/Build/numpty-eval/ and put this spike's set under it.

0. ~/Build/numpty-eval/ layout (saturn):
   - convert/: gguf_add_decision.py, fork_prompt.py, winnow_systemone.jinja, quyet_systemone.jinja, models-ini-preset.txt, convert_and_start.sh, convert.log. Delete the empty quyet-download.log.
   - probes/nump-022/: compare_prompts.py, image_probe.py, vram_and_images.sh, requests.json, replica.json, parity-requests.json, decisions.json, decisions.fork.json, esc-request.json, esc-request.fork.json, answers8099.json, server8099.log, server8099--c8192.log, server8099--c32768.log.
   - venv/: recreate the gguf venv here (python3 -m venv, pip install numpy tqdm pyyaml pillow), check `PYTHONPATH=~/Build/llama.cpp/gguf-py venv/bin/python -c "import gguf"`, then delete ~/Build/venv-gguf. A moved venv keeps absolute paths, so recreate instead of mv.
   - imagejev-preview/: this spike (items, images/, manifest items.jsonl, runs/<model>-<image|text>.jsonl, the builder and runner scripts).
   - ~/Build/llama.cpp stays: it is the source of the /opt/llama binaries, not an eval artefact (assumption; say so in the notes). dalai, dotwiz, everywhereml, pygments-* are unrelated projects and are not touched.
   - After the move: update doc-008 "What is not in the repo" and doc-009 (paths under ~/Build) with `backlog doc update`, and the saturn memory file.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Handoff for a new context (planning session 2026-10-08). Read the plan first; this note holds what the probe already established so it is not redone.

Pinned inputs (re-download; cheap): raw.githubusercontent.com/fstandhartinger/model-market-comparison/9f20f1e47991b005aa1811b6be435a7f32b4f2cf/data/raw/benchmarks/jevbench/multimodal-preview/{preview.json, source/items-extended-real.json, source/RUN-RESULT.md, source/results-gemini.json, source/results-gemini-extension.json, source/results-luna.json, source/results-luna-extension.json, source/results-openjev-real.log}. sha256 prefixes: see the next note.

Item list facts: 128 items, all type choice; criteria sizes 2 (22 items), 4 (58), 5 (48); keys A..E for ArxivQA, ScreenSpot, Mind2Web, option_0..3 for Geometry3K and FinQA (18 of 20), yes/no for CLEVR and FinQA mm-069, mm-074. Fields: id, dataset, source_row, split, image, state{image, source, +platform/element_type (ScreenSpot), +website/domain (Mind2Web)}, rubric{type, instructions, criteria}, gold, gold_origin, transformation, source_label (ScreenSpot: bbox_xyxy normalised, instruction, file_name; Mind2Web: action_uid, operation, positive_backend_node_id). Source rows: CLEVR [1,11..20,22,23,24,26,29,30,32,35,36]; Geometry3K, ArxivQA, FinQA, Mind2Web rows 0..n-1; ScreenSpot [0-8, 162-170, 334-342, 468-476] (platform blocks).

Hugging Face mapping, verified with datasets-server /rows on 2026-10-08: CLEVR-HOPE config HOP00 split test_complex_ood, field idx = source_row, fields query/answer/image (rows 1, 11, 36 equal). Geometry3K default/test: images[0], problem (starts with <image>), answer. ArxivQA default/train: media[0], messages (JSON with question and options A-D), answer. FinQA (bevaya) default/test: table_ori (list of rows), question, answer, exe_ans; row 0 answer 94 = gold option_2. ScreenSpot (bevaya) default/test: file_name, bbox (normalised xyxy), instruction, data_type, data_source, image. Mind2Web (osunlp) default/test_task: action_uid, operation, pos_candidates / neg_candidates (JSON strings with attributes.bounding_box_rect "x,y,w,h" and backend_node_id), confirmed_task, website, domain, screenshot (full page, e.g. 1280x4171). Revisions the server reported: geometry3k fd21e533, ArxivQA e13bb29f, ScreenSpot 0be08781, Mind2Web 1b4c6a8c (record the full sha when building).

Preview-round per-dataset results (all 128): openjev 4B: ArxivQA 9/20, CLEVR 15/20, FinQA 7/20, Geometry3K 19/20, Mind2Web 9/12, ScreenSpot 1/36 (60/128, p50 0.165 s). Gemini 3.1 Flash-Lite: 15, 14, 11, 12, 10/36, 11/12 (73). Luna: 16, 20, 13, 13, 5/36, 9/12 (76). Gemini usage shows 1,080 image tokens per item.

Board (benchmarkheaven.com/image-jev-bench, v0.3.0 built 2026-10-07, 2,441 items on 2,160 images, 300 public / 1,200 sealed draw; self-hosted rows measured on S+P, APIs on A+P): Clef-Flash Capability 52.2, Intelligence 37.3, Calibration 67.2, Cost 42.2, $0.084 per 1,000, public set P n 235 correct 130 (0.553) ECE 0.189; Clef 58.1; Winnow-12B (Q8_0 + F16 vision projector) 50.0, I 38.6, C 61.4, P 138/235 (0.587, probability coverage 0.894) ECE 0.161, S 550/939. Board public example items include ScreenSpot item 15 (mm-135) and 341 (mm-118) and Geometry3K item 8 (mm-029), so the v0.3 pool overlaps the preview sources but item ids differ. Submission page: "Submit a model" link on the board; read it for AC #5.

Request shape (doc-009 AC #6): POST /v1/systemone {model, state, questions, images: [data URL]}; the template puts one media marker per image before State:. Quyet image request costs about 85 extra input tokens and 1.7 s warm in that probe; Clef-Flash about 8x faster. Confirm with one smoke item per model before the full passes. Pillow is not installed on the Mac; use a uv inline script (dependencies = ["pillow"]).

Mac scratch of this session (may be gone): /private/tmp/claude-503/-Users-waylonflinn-Development-numpty/96458379-6727-4456-b3e2-f677c507c968/scratchpad/preview/.

sha256 prefixes of the pinned files (full hashes to be recorded in doc-010): items-extended-real.json 616a9bd6c4ed378e, RUN-RESULT.md 03ddf72b2cd0f63f, results-gemini.json 8ae91254320c62b7, results-gemini-extension.json f3d23972b2d1af88, results-luna.json e1b127b6df910274, results-luna-extension.json 7e274694f0c321f5, results-openjev-real.log c50add7c5b8e88f4, preview.json 475ae88798f1f464.

Session 2 (2026-10-08). Step 0 done: saturn ~/Build tidied into ~/Build/numpty-eval/{convert,probes/nump-022,venv,imagejev-preview}; venv recreated (gguf import checked), venv-gguf and the empty quyet-download.log deleted; moved scripts' paths patched; doc-008 and doc-009 paths updated. Step 2 done: builder (scratch tools/build.py, uv + pillow) rebuilt all 128 items of items-extended-real.json (the file has no synthetic items; 36+20+20+20+20+12). All source checks pass (question, options, gold; ScreenSpot file_name/bbox/instruction/platform/type; Mind2Web action_uid/positive id/operation/task/website). Rows via datasets-server /rows in windows (429 backoff); revisions: CLEVR-HOPE 2d0c19f2, geometry3k fd21e533, ArxivQA e13bb29f, FinQA 3d6a736b, ScreenSpot 0be08781, Mind2Web 1b4c6a8c. Rules: FinQA table_ori rendered with Pillow default TTF 20 px, grid, header shaded; ScreenSpot markers r=max(16, 2.2% of min side), gold at bbox centre, distractors from random.Random(item id) in [4%,96%], rejected inside bbox+2r or within 5r of another marker, letters A..E minus gold in reading order; Mind2Web boxes = positive + first four negatives (dataset order) that are non-degenerate, inside the screenshot, under 10% of a width x 900 viewport, and do not contain the positive rect; crop = width x 900 window centred on the boxes' union (taller if needed); labels above the box or inside it at the crop edge. Smoke (4 items x 2 models x image/text) OK: images accepted by both presets through the router. Step 3 running: four passes, runs/<model>-<image|text>.jsonl.

Step 3-5 done 2026-10-08. Four passes, 512 requests, 0 errors (run.log on saturn). Results: clef-flash-9b-Q8 image 109/128 (image reasoning 66/80, GUI 43/48), Brier 0.235, ECE 0.085, p50 0.49 s, 1,416 tokens; quyet-large-Q4 image 101/128 (58/80, 43/48), Brier 0.317, ECE 0.099, p50 0.60 s, 375 tokens; text controls 54 and 53 of 128. Paired: 14 Clef-only vs 6 Quyet-only (exact p 0.115); CLEVR-HOPE 7 vs 0 (p 0.016), Quyet with image 13 < without 14. Both above every preview system (Luna 76, Gemini 73). Comparability caveat: our ScreenSpot distractors are random points, easier than the preview's. doc-010 written with backlog doc update; decision-004 created with the CLI, body written below the frontmatter (no CLI path for decision content, as for decision-001/003). Set, runs and scripts on saturn ~/Build/numpty-eval/imagejev-preview/ (28 MB); Mac scratch holds raw/ too. Submit page read: needs a public HF/GitHub link or https API; the board already measures a Winnow-12B Q8_0 + F16 projector GGUF.

2026-10-08 review: decision-004 amended with the cause (text-only LoRA on the stock Gemma 4 projector, doc-009) and a retest trigger: a Quyet or Gemma 4 LoRA release whose adaptation includes images reruns the four passes on the rebuilt set.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-10-08 21:54
---
Plan ready for review
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Rebuilt all 128 items of the ImageJevBench preview round from the pinned item list (9f20f1e) and the Hugging Face source rows, every source check passing (60 exact, 68 approximate with recorded rules), manifest with image sha256. Ran quyet-large-Q4 and clef-flash-9b-Q8 with the image and text-only through the saturn router (512 requests, no errors). Clef-Flash 109/128, Brier 0.235, ECE 0.085; Quyet 101/128, Brier 0.317, ECE 0.099; text controls 54 and 53. Clef-Flash wins on CLEVR-HOPE (20 vs 13, p 0.016) and ArxivQA, ties on GUI, tables and geometry. decision-004 returns the image row to Clef-Flash with Quyet+mmproj as the resident-model fallback, and states the Benchmark Heaven condition (a Quyet variant beating Clef-Flash on this set at p<0.05, published as GGUF+mmproj on HF). Verified by scores.json/compare.json from the raw run files (doc-010 tables). Also step 0: saturn ~/Build tidied into ~/Build/numpty-eval/, doc-008/doc-009 paths updated.
<!-- SECTION:FINAL_SUMMARY:END -->
