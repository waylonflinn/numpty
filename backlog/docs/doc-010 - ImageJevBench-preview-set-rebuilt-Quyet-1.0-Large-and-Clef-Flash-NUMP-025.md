---
id: doc-010
title: 'ImageJevBench preview set rebuilt: Quyet-1.0-Large and Clef-Flash (NUMP-025)'
type: specification
created_date: '2026-10-08 23:29'
updated_date: '2026-10-08 23:32'
tags:
  - research
  - decision-models
---
## Question

decision-003 gave Quyet-1.0-Large (preset `quyet-large-Q4`, Gemma 4 mmproj) the image row of the requirement-to-model table on one synthetic probe and marked the row provisional. This spike rebuilds the only item-level ImageJevBench set in the open, the 128-item private preview round of September 2026, runs it against `quyet-large-Q4` and `clef-flash-9b-Q8` with and without the image, and settles the row. The decision is decision-004.

Everything measured here ran on 2026-10-08 through the saturn router from the Mac with the doc-008 settings: one request per item, sequential, no retries, latency measured on the Mac. Nothing in this spike entered the repo. The builder, the rebuilt images, the manifest, the runner, the scorer and the raw responses are on saturn under `~/Build/numpty-eval/imagejev-preview/`.

## Sources and pins

Item list and preview results: `fstandhartinger/model-market-comparison`, commit `9f20f1e47991b005aa1811b6be435a7f32b4f2cf` (2026-09-21), directory `data/raw/benchmarks/jevbench/multimodal-preview/`. Copies are in `pinned/` on saturn.

| file | sha256 | content |
|---|---|---|
| `source/items-extended-real.json` | `616a9bd6c4ed378ec3382b68db17d5c2b9ad19f164d35a75f8bb5238317a7060` | 128 choice items: id, dataset, source_row, split, rubric, gold, gold_origin, transformation, source_label. No synthetic items: the 8 Z-Image-Turbo items are not in this file. |
| `source/RUN-RESULT.md` | `03ddf72b2cd0f63fd4455682ca0bb69bd47f7052b67215821dab29be25707ed9` | the six preview systems, aggregate per subset |
| `source/results-gemini.json`, `-extension.json` | `8ae91254320c62b743b595cad60538f802f823fc7d15f98abbfbc5938046dc06`, `f3d23972b2d1af88abe845180301182b67e2085413cc60972453475641e18625` | Gemini 3.1 Flash-Lite per item (110 + 18), with token usage: 1,080 to 1,100 image tokens per item |
| `source/results-luna.json`, `-extension.json` | `e1b127b6df910274d9bc071685e1ce256f045e3cd0b2f2e2c2827736b7ba36fb`, `7e274694f0c321f5962ce6c190fca86c562fdc3f146ebeaad81173fae56cb0c3` | GPT-5.6 Luna per item (110 + 18) |
| `source/results-openjev-real.log` | `c50add7c5b8e88f471b1bc42ab7181ef386a1dab7a3d1dd1915b1a470a4308cb` | AlexWortega/openjev 4B v2 BF16, ok/miss per item and a summary line |
| `preview.json` | `475ae88798f1f4644624a7bc7ae3b15f68c2a96ff14445dd68b591185305ab26` | the preview manifest |

Per-item results exist for openjev 4B v2, Gemini 3.1 Flash-Lite and Luna. djev-dev, decider-2b-vision and reflex 4B have aggregates only.

Hugging Face source rows, read with the datasets-server `/rows` endpoint on 2026-10-08 (the revision is the `sha` the Hub API reported that day):

| dataset | repo | config / split | revision | row field that equals the item |
|---|---|---|---|---|
| CLEVR-HOPE | `user9000/CLEVR-HOPE` | `HOP00` / `test_complex_ood` | `2d0c19f23dc5de19f83f4e9928a793c95632327a` | `idx` = source_row, `query`, `answer`, `image` |
| Geometry3K | `hiyouga/geometry3k` | `default` / `test` | `fd21e533e1e50d0662a2bf7b223e60511bd5f8b7` | `problem` (after `<image>`), `answer`, `images[0]` |
| ArxivQA | `mm-eval/ArxivQA` | `default` / `train` | `e13bb29ff5b2c2ae5f05cc0b1ecc2b24a6833c81` | `messages[0].question`, `.options`, `answer`, `media[0]` |
| FinQA | `bevaya/FinQA` | `default` / `test` | `3d6a736bc67e06bc15fbf3618d88204a57c5b25e` | `question`, `exe_ans` or `answer`, `table_ori` |
| ScreenSpot | `bevaya/ScreenSpot` | `default` / `test` | `0be08781e2e188582f6131625ae1598d443b4d5d` | `file_name`, `bbox`, `instruction`, `data_source`, `data_type`, `image` |
| Multimodal-Mind2Web | `osunlp/Multimodal-Mind2Web` | `default` / `test_task` | `1b4c6a8cf9f77b7a5e0d641959935c80c4a05889` | `action_uid`, `operation`, `pos_candidates`, `neg_candidates`, `confirmed_task`, `website`, `screenshot` |

Board: benchmarkheaven.com/image-jev-bench, v0.3.0 built 2026-10-07, 2,441 items on 2,160 images, 300 public and 1,200 sealed in the draw. Self-hosted rows are measured on sealed plus public, API rows on an API draw plus public. Submission page: benchmarkheaven.com/submit.

## Rebuild (AC #1)

The builder (`build.py`, uv inline script, Pillow) reads the item list, fetches each source row, checks the row against the item, and writes `images/<id>.<ext>` and the manifest `items.jsonl`. All 128 items pass every check. The 8 synthetic items are out of scope and are not in the item list.

| dataset | items | rebuild | gold | checks against the source row | image |
|---|---|---|---|---|---|
| CLEVR-HOPE | 20 | exact: image and question verbatim | equal | `idx`, question, answer | 480 x 320 JPEG as served |
| Geometry3K | 20 | exact: image and question verbatim | equal (numeric compare with the gold option text) | question, answer | PNG as served, 238 to 654 px |
| ArxivQA | 20 | exact: image and question verbatim, options from the item list equal the row | equal | question, options, answer | JPEG as served, long side 2,016 px on 18 of 20 |
| FinQA | 20 | approximate image, exact gold: `table_ori` rendered with Pillow; distractors from the item list | equal (`exe_ans` or `answer`, numeric compare; two yes/no items) | question, answer | PNG, 255 to 1,217 px wide |
| ScreenSpot | 36 | approximate: five lettered markers drawn on the source screenshot | gold letter from the item list, marker centred on the labelled bbox | `file_name`, `bbox`, `instruction`, platform, element type | PNG, 960 x 540 to 2,360 x 1,640 and 1,080 x 2,400 |
| Multimodal-Mind2Web | 12 | approximate: five boxed and labelled candidates on a crop of the source screenshot | gold letter from the item list on the positive candidate | `action_uid`, positive `backend_node_id`, operation, task text, website | JPEG, 1,280 x 900 crop |

Rules for the 68 approximate items. These rules are ours. The preview round describes its procedure in the `transformation` field but does not ship the code, so our images differ from the preview images in layout.

- FinQA: default Pillow TrueType font at 20 px, one table row per line, header row shaded, grid lines, cell padding 10 px, row height 34 px.
- ScreenSpot: marker radius `max(16, 2.2 % of the shorter side)`. The gold marker is at the centre of the labelled bbox. The four distractors come from `random.Random(item id)`, each a point in the central 92 % of the image, rejected when it falls inside the bbox grown by two radii or within five radii of another marker. The letters A to E minus the gold letter go to the distractors in reading order (top to bottom, then left to right). Distractors are random points, so they often sit on empty screen, not on other controls. This is easier than a rule that places distractors on other clickable elements.
- Multimodal-Mind2Web: boxes are the positive candidate and the first four negative candidates, in dataset order, whose rect is non-degenerate, inside the screenshot, under a tenth of a 1,280 x 900 viewport in area, and does not contain the positive rect. Letters as for ScreenSpot. The crop is a full-width 900 px window centred on the union of the boxes, taller when the union needs it. The label sits above the box, or inside its top-left corner when the box touches the crop edge.

Manifest `items.jsonl`, sha256 `10840739fb98588b9cb8f043d9153d7ddd8f9106362d5ebbc1f54841fdb00546`, one line per item: id, dataset, repo, config, split, row, revision, kind (`verbatim`, `rendered`, `markers`, `boxes`), image file, image sha256, size, the check results, subset, question, criteria, gold, state, and the build record (marker or box coordinates, crop window, table rows). Rebuilt images total 23 MB. The raw source rows and images (20 MB) are in `raw/` on the Mac scratch only.

Caveat on the verbatim images: the datasets-server serves images from its asset cache. CLEVR-HOPE came as JPEG and 18 of 20 ArxivQA images have a long side of exactly 2,016 px, so the cache may re-encode or cap large images. The parquet shards (ArxivQA: 36 shards of about 550 MB) were not downloaded to check. The preview round stored WebP copies of unknown size, so neither set is the raw dataset image.

## Run (AC #2)

Request per item: `POST /v1/systemone` with `model`, `state` = the item state without the image path (`source`, plus `platform` and `element_type` for ScreenSpot, `website` and `domain` for Mind2Web), one question `q` of type `choice` with the rubric instructions and criteria verbatim, and `images = [data URL]` of the rebuilt image. The text-only control sends the same body without `images`. Four passes of 128 requests, 2026-10-08, no errors, timings in `run.log`.

| pass | first request (load) | warm p50 | warm p95 | warm max | input tokens mean (min to max) |
|---|---|---|---|---|---|
| quyet-large-Q4, image | 4.56 s | 0.60 s | 1.31 s | 1.51 s | 375 (133 to 717) |
| quyet-large-Q4, text | 0.14 s | 0.17 s | 0.27 s | 0.43 s | 96 (57 to 229) |
| clef-flash-9b-Q8, image | 3.44 s | 0.49 s | 4.30 s | 5.61 s | 1,416 (234 to 4,191) |
| clef-flash-9b-Q8, text | 0.34 s | 0.15 s | 0.23 s | 0.28 s | 202 (138 to 341) |

Image tokens by dataset (mean `usage.input_tokens` with the image): Quyet 143 CLEVR, 172 Geometry3K, 581 ArxivQA, 188 FinQA, 523 ScreenSpot, 624 Mind2Web. Clef-Flash 303, 319, 2,965, 360, 2,378, 1,393. Clef-Flash spends 3 to 5 times more tokens on large images, which is where its p95 comes from. Inference: the Gemma 4 projector pools each image to fewer tokens than Clef-Flash's vision path, so Quyet sees large screenshots and charts at lower effective resolution.

## Results (AC #2 and #3)

Correct answers. Chance is the mean of 1 / options.

| run | CLEVR-HOPE 20 | Geometry3K 20 | ArxivQA 20 | FinQA 20 | ScreenSpot 36 | Mind2Web 12 | image reasoning 80 | computer and browser use 48 | all 128 |
|---|---|---|---|---|---|---|---|---|---|
| clef-flash-9b-Q8, image | **20** | **19** | **15** | 12 | **32** | **11** | **66** (82.5 %) | **43** (89.6 %) | **109** (85.2 %) |
| quyet-large-Q4, image | 13 | **19** | 12 | **14** | **32** | **11** | 58 (72.5 %) | **43** (89.6 %) | 101 (78.9 %) |
| clef-flash-9b-Q8, text | 16 | 15 | 12 | 4 | 5 | 2 | 47 | 7 | 54 (42.2 %) |
| quyet-large-Q4, text | 14 | 16 | 11 | 4 | 7 | 1 | 45 | 8 | 53 (41.4 %) |
| chance | 0.50 | 0.25 | 0.25 | 0.28 | 0.20 | 0.20 | 0.32 | 0.20 | 0.27 |

Calibration and cost on all 128. Brier is the multi-class sum of squares against the one-hot gold. ECE uses 10 equal-width bins on p_max, as in `scripts/eval/harness.py`.

| run | accuracy | Brier | ECE | mean p_max | p50 s | mean input tokens |
|---|---|---|---|---|---|---|
| clef-flash-9b-Q8, image | **0.852** | **0.235** | **0.085** | 0.787 | **0.49** | 1,416 |
| quyet-large-Q4, image | 0.789 | 0.317 | 0.099 | 0.780 | 0.60 | **375** |
| clef-flash-9b-Q8, text | 0.422 | 0.668 | 0.041 | 0.459 | 0.15 | 202 |
| quyet-large-Q4, text | 0.414 | 0.628 | 0.128 | 0.446 | 0.17 | 96 |

Brier / ECE per dataset, image passes:

| run | CLEVR-HOPE | Geometry3K | ArxivQA | FinQA | ScreenSpot | Mind2Web | image reasoning | computer and browser use |
|---|---|---|---|---|---|---|---|---|
| clef-flash-9b-Q8 | 0.031 / 0.071 | 0.182 / 0.168 | 0.508 / 0.331 | 0.453 / 0.183 | 0.123 / 0.101 | 0.184 / 0.259 | 0.293 / 0.095 | 0.138 / 0.126 |
| quyet-large-Q4 | 0.471 / 0.229 | 0.169 / 0.194 | 0.555 / 0.227 | 0.406 / 0.132 | 0.188 / 0.100 | 0.149 / 0.159 | 0.400 / 0.118 | 0.179 / 0.106 |

Image minus text (AC #3), correct answers with the image minus correct answers without it:

| model | CLEVR-HOPE | Geometry3K | ArxivQA | FinQA | ScreenSpot | Mind2Web | all 128 |
|---|---|---|---|---|---|---|---|
| clef-flash-9b-Q8 | +4 | +4 | +3 | +8 | +27 | +9 | **+55** |
| quyet-large-Q4 | **-1** | +3 | +1 | +10 | +25 | +10 | +48 |

Both models answer the text-only control a little above chance (41 to 42 % against 27 %), from the question text alone: Geometry3K and CLEVR questions carry prior information, and the GUI items do not (5 to 8 of 48, chance 9.6). The image accounts for 48 of Quyet's 101 and 55 of Clef-Flash's 109 correct answers.

Paired comparison of the two image passes (exact two-sided binomial test on the discordant items):

| subset | Clef-Flash only | Quyet only | p |
|---|---|---|---|
| all 128 | 14 | 6 | 0.115 |
| image reasoning 80 | 12 | 4 | 0.077 |
| computer and browser use 48 | 2 | 2 | 1 |
| CLEVR-HOPE 20 | 7 | 0 | 0.016 |

Reading. The two models agree on 95 correct and 13 wrong of the 128 items. The whole gap is on the image-reasoning half, and most of it is CLEVR-HOPE, where Quyet with the image (13) does worse than Quyet without it (14): on 7 synthetic scenes the image path flips a correct text prior. Its CLEVR misses are confident (p_max 0.61 to 0.98), which is the 0.471 Brier. On the GUI items, on FinQA tables and on Geometry3K diagrams Quyet with the mmproj equals Clef-Flash. The items every system misses are mm-043, mm-051, mm-055 (ArxivQA), mm-079 (FinQA) and mm-116 (ScreenSpot).

## Comparison with the preview round and the board (AC #4)

Preview-round systems on the same 128 items (RUN-RESULT.md, BF16 on an H200 for the local models):

| system | image reasoning 80 | computer and browser use 48 | all 128 | p50 |
|---|---|---|---|---|
| clef-flash-9b-Q8 (this doc) | 66 | 43 | 109 | 0.49 s |
| quyet-large-Q4 (this doc) | 58 | 43 | 101 | 0.60 s |
| GPT-5.6 Luna | 62 | 14 | 76 | 6.13 s |
| Gemini 3.1 Flash-Lite | 52 | 21 | 73 | 1.20 s |
| djev-dev BF16 | 43 | 18 | 61 | 0.17 s |
| openjev 4B v2 BF16 | 50 | 10 | 60 | 0.165 s |
| decider-2b-vision BF16 | 45 | 10 | 55 | 0.090 s |
| reflex 4B BF16 | 46 | 9 | 55 | 0.140 s |

Per dataset against the three systems with per-item results:

| system | CLEVR-HOPE | Geometry3K | ArxivQA | FinQA | ScreenSpot | Mind2Web |
|---|---|---|---|---|---|---|
| clef-flash-9b-Q8 | 20 | 19 | 15 | 12 | 32 | 11 |
| quyet-large-Q4 | 13 | 19 | 12 | 14 | 32 | 11 |
| Luna | 20 | 13 | 16 | 13 | 5 | 9 |
| Gemini 3.1 Flash-Lite | 14 | 12 | 15 | 11 | 10 | 11 |
| openjev 4B v2 | 15 | 19 | 9 | 7 | 1 | 9 |

Per-item agreement (`compare.json`): on the 80 image-reasoning items Clef-Flash agrees with Luna on 66 (57 both right, 9 both wrong) and Quyet with Luna on 66. On the 48 GUI items both of our models get 43, where Luna gets 14 and Gemini 21: 31 items that Clef-Flash gets and Luna misses, 2 the other way.

What is comparable:

- The 60 CLEVR-HOPE, Geometry3K and ArxivQA items are the same question, options and gold, and the same source image up to the serving format. On these 60 Clef-Flash scores 54 against Luna 49, Gemini 41 and openjev 43. Quyet scores 44. This is the comparable part, and it puts both quantized local models at or above the preview systems.
- Chance, the gold and the number of options are equal on all 128.

What is not comparable:

- The 68 approximate items (FinQA, ScreenSpot, Mind2Web) use our rendering, marker and crop rules. The ScreenSpot distractors are random points, often on empty screen. Our 32 of 36 against the preview's best of 10 of 36 (Gemini) says the preview's markers were harder, not that our models are three times better at grounding. The text-only control (5 to 7 of 36) shows the image does the work, but the task our images pose is easier than the preview's.
- Quantization: Q4_K_M (Quyet) and Q8_0 (Clef-Flash) against BF16 for the four local preview systems.
- Prompt wrapper: the preview round's prompt and decoding are not published. Our requests use the upstream decision-model path of each preset.
- Hardware: the preview p50 figures are H200 (local) or API latency. Ours include the tailscale hop.
- Board: ImageJevBench v0.3.0 draws from a 2,441-item pool that overlaps the preview sources (public examples include ScreenSpot items 15 and 341 and Geometry3K item 8) but has different items and ids, 1,200 sealed. Clef-Flash's board row is Capability 52.2, Intelligence 37.3, Calibration 67.2, public set 130 of 235 (0.553), ECE 0.189. Our 109 of 128 (0.852) and ECE 0.085 on the preview set are not that measurement. The board also lists Winnow-12B (Q8_0 + F16 vision projector) at 50.0, Intelligence 38.6, public 138 of 235, ECE 0.161: an image-untrained Gemma 4 LoRA with the stock projector, the same construction as Quyet plus mmproj, scores 2.2 under Clef-Flash there. That matches the direction of our result.

## What the result says for the image row

1. Clef-Flash beats Quyet with the mmproj on the rebuilt set: 109 against 101, Brier 0.235 against 0.317, ECE 0.085 against 0.099, p50 0.49 s against 0.60 s, at 13.8 GB against 22.3 GB. The gap is not significant at 0.05 on all 128 (p 0.115) but it is one-directional: 14 items against 6, and significant on CLEVR-HOPE.
2. Quyet's image path is usable. 101 of 128 is above every preview system, it equals Clef-Flash on GUI grounding, tables and geometry, and it costs a quarter of the image tokens. It loses on synthetic 3D scenes and on charts, where the untrained projector shows.
3. The condition under which the image row goes to Quyet is a Quyet variant that beats Clef-Flash on this set with more Quyet-only than Clef-Flash-only items at p < 0.05, that is at least about 12 net discordant items in its favor on the 128.

## Benchmark Heaven submission

The submit page (read 2026-10-08) takes a model name, at least one of a GitHub link, a Hugging Face link or a public https API URL, an email, and the benchmarks to run. The regular queue is free, the fast lane is paid. Self-hosted models are measured by the board itself, so the GGUF plus mmproj must be public: saturn is not. The board already measures a Winnow-12B Q8_0 GGUF with an F16 projector, so the construction is accepted.

A submission of the Quyet conversion to ImageJevBench is worth it only when the condition in item 3 above holds. Today it does not: the board's own Clef-Flash row is the reference, and Quyet trails Clef-Flash on our set. A JevBench (text) submission is a separate question and out of scope here. Publishing the GGUF is the NUMP-023 recipe (Winnow), not this task.

## Reproduce

On saturn, `~/Build/numpty-eval/imagejev-preview/`: `pinned/` (the item list and preview results), `images/` (128 rebuilt images), `items.jsonl` (manifest), `runs/<model>-<image|text>.jsonl` (one raw response per item, with latency and token usage), `scores.json`, `compare.json`, `run.log`, and the scripts `build.py` (uv, Pillow), `run.py`, `score.py` (imports `brier`, `ece` from `scripts/eval/harness.py`), `compare.py`. The builder fetches rows in windows of up to 100 and backs off 30 s on HTTP 429.

If the set proves useful, moving the runner into `scripts/eval/` and the results under `scripts/eval/results/` is a chore, not this task.

## Sources

- https://github.com/fstandhartinger/model-market-comparison/tree/9f20f1e47991b005aa1811b6be435a7f32b4f2cf/data/raw/benchmarks/jevbench/multimodal-preview/source
- https://benchmarkheaven.com/image-jev-bench and https://benchmarkheaven.com/submit (2026-10-08)
- https://github.com/fstandhartinger/jevbench/tree/bb05a33/results/imagejevbench/v0.1.3 (aggregate results and method only)
- The six Hugging Face datasets in the table above, through https://datasets-server.huggingface.co/rows
- doc-008 (protocol, metrics), doc-009 (Quyet conversion, image request shape), decision-003 (the provisional image row)
