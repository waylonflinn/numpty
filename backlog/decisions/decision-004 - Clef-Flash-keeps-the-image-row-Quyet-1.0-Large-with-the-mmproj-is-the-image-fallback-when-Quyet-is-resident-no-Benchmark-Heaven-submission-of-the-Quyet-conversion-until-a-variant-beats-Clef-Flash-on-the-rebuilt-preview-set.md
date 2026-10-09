---
id: decision-004
title: >-
  Clef-Flash keeps the image row; Quyet-1.0-Large with the mmproj is the image
  fallback when Quyet is resident; no Benchmark Heaven submission of the Quyet
  conversion until a variant beats Clef-Flash on the rebuilt preview set
date: '2026-10-08 23:29'
status: accepted
---
## Context

decision-003 moved the image row of the requirement-to-model table from Clef-Flash to Quyet-1.0-Large with the Gemma 4 mmproj on one synthetic probe, and marked the row provisional because Quyet never trained on images. NUMP-025 rebuilt the 128-item ImageJevBench preview set (doc-010) from the pinned item list and the Hugging Face source rows, with equal gold on all 128 and exact images on 60, and ran it against `quyet-large-Q4` and `clef-flash-9b-Q8` through the saturn router with the image and without it, doc-008 settings, 2026-10-08.

| criterion | Clef-Flash-9B Q8_0 | Quyet-1.0-Large Q4_K_M + mmproj | prefer |
|---|---|---|---|
| all 128, correct | **109** (85.2 %) | 101 (78.9 %) | Clef-Flash (14 items only Clef-Flash, 6 only Quyet, p 0.115) |
| image reasoning 80 | **66** | 58 | Clef-Flash (12 against 4, p 0.077) |
| CLEVR-HOPE 20 | **20** | 13 (14 without the image) | Clef-Flash (7 against 0, p 0.016) |
| Geometry3K, FinQA, ScreenSpot, Mind2Web | 19, 12, 32, 11 | 19, 14, 32, 11 | tie |
| computer and browser use 48 | 43 | 43 | tie |
| Brier / ECE, all 128 | **0.235 / 0.085** | 0.317 / 0.099 | Clef-Flash |
| image gain over the text-only control | **+55** | +48 | Clef-Flash |
| warm p50 / p95 with an image | **0.49 s** / 4.30 s | 0.60 s / **1.31 s** | Clef-Flash at p50, Quyet on large images |
| image tokens, mean | 1,416 | **375** | Quyet |
| VRAM | **13.8 GB** | 22.3 GB | Clef-Flash |

The likely cause of the gap is the adaptation, not the base model. Quyet-1.0-Large is a Gemma-4-31B-it LoRA merged on text-only decision data (doc-009); the vision path is the stock Gemma 4 projector, which the LoRA never touched. The decision head therefore reads image features it was not trained against, and that shows exactly where image understanding must carry the answer (synthetic scenes, charts) and not where the text prior or a marker letter suffices. An adaptation that includes images is likely to swing this comparison the other way.

Both quantized local models score above every system of the preview round (best: Luna 76, Gemini 3.1 Flash-Lite 73). On the 60 exact items Clef-Flash has 54 and Quyet 44 against Luna 49. The 68 approximate items use our marker, crop and table rules, so the GUI figures are not comparable with the preview round or the board. The board's own Winnow-12B Q8_0 plus F16 projector row (the same construction as Quyet plus mmproj) sits 2.2 under Clef-Flash, in the same direction.

## Decision

1. The image row of decision-003 returns to Clef-Flash Q8_0. Quyet with the mmproj stays as the fallback for image questions when Quyet is the resident model and a load is not wanted: it is usable (101 of 128, equal to Clef-Flash on GUI grounding, tables and geometry) but loses on synthetic scenes and charts, and its wrong answers there are confident.
2. The requirement-to-model table now reads:

| requirement | model | reason |
|---|---|---|
| text only, accuracy on choice and score questions | Quyet-1.0-Large Q4_K_M | decision-003, unchanged |
| image input | **Clef-Flash Q8_0**; Quyet-1.0-Large Q4_K_M with mmproj when Quyet is resident | 109 against 101, better Brier and ECE, 8.5 GB less VRAM |
| calibrated probabilities | Quyet-1.0-Large Q4_K_M (text); Clef-Flash Q8_0 (images) | decision-003 for text; Brier 0.235 against 0.317 with images |
| throughput, several questions on one state | Clef-Flash Q8_0 | decision-003, unchanged |
| VRAM headroom | Clef-Flash Q8_0 or Winnow-12B Q8_0 | decision-003, unchanged |

3. Retest trigger: a Quyet (or other Gemma 4 LoRA) release whose adaptation includes image data reopens this decision. Rerun the four passes on the rebuilt set, same scripts, and expect the image row to move. A larger quant of the same text-only LoRA is not expected to change the result and does not trigger a retest on its own.
4. No Benchmark Heaven submission of the Quyet conversion to ImageJevBench. The condition for one: a Quyet variant that beats Clef-Flash on the rebuilt preview set with more Quyet-only than Clef-Flash-only discordant items at p < 0.05 (about 12 net items on 128), published as a GGUF plus mmproj on Hugging Face (the NUMP-023 recipe), and submitted through benchmarkheaven.com/submit with the Hugging Face link and ImageJevBench checked. The board measures self-hosted models itself and already accepts a GGUF plus projector (Winnow-12B row).
5. The rebuilt set is the local image regression set. It lives on saturn under `~/Build/numpty-eval/imagejev-preview/` with the manifest and raw responses. Promoting the runner into `scripts/eval/` is a chore when a second image model needs measuring.

## Consequences

- numpty docs name Clef-Flash as the local image decision model and Quyet as the text model. A workload that mixes text and image questions chooses between a model switch (4.6 s load for Quyet, 3.4 s for Clef-Flash) and Quyet's weaker image path.
- decision-003 items 1, 3, 4 and 5 stand. Its row "image input" and the image part of "calibrated probabilities" are superseded by this record.
- The doc-006 watch gains two items: a Quyet-1.0-Large release whose adaptation includes images (the retest trigger in item 3), and an ImageJevBench board row for any Quyet build.
- The ScreenSpot distractor rule (random points) makes the GUI half of the set easy. If the set is reused for a decision on GUI grounding, a harder rule (distractors on other labelled controls) is needed first.
