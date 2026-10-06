---
id: doc-006
title: 'Decision model watch: ggml-org GGUFs vs JevBench'
type: other
created_date: '2026-10-05 23:14'
updated_date: '2026-10-06 00:17'
tags:
  - research
  - recurrent
  - decision-models
---
# Decision model watch: ggml-org GGUFs vs JevBench

Recurrent cross-reference for NUMP-016.01. Joins the GGUF decision models that upstream llama.cpp serves at `/v1/systemone` (the ggml-org Hugging Face collection "Decision models") with the public JevBench board, and states which quants fit the deployment target. Protocol and mechanism detail lives in doc-005; this doc does not repeat it. This doc does not make the NUMP-007 model decision (NUMP-016 AC #5); it feeds it.

One dated section is added per run, newest first. Fixed sections (sources, procedure, fit method) come first.

## Sources and refresh procedure

All sources are machine-readable. The script `scripts/jev_xref.py` (uncommitted, stdlib only) pulls them and prints the catalog, score, evidence, fit, header, and watch tables as Markdown:

```
python3 scripts/jev_xref.py --release v1.6.0 --cache <dir> --json <out.json>
```

1. Collection: `GET https://huggingface.co/api/collections/ggml-org/decision-models`. Gives the repo list and `lastModified` per repo. Diff against the previous run's catalog.
2. Per repo: `GET https://huggingface.co/api/models/<repo>?blobs=true`. Gives `cardData.license`, `cardData.base_model`, and every file with its size.
3. GGUF header of the Q8_0 file per repo, read with an HTTP Range request (about 1 MB, no download): `general.architecture`, `general.size_label`, `{arch}.decision.*` (type, temperatures, buckets), block count, head counts, head sizes, context length. The reader stops at the tokenizer arrays, so chat templates are not read (doc-005 verified the `systemone` template on Kev-4B and OpenJev by other means).
4. JevBench: `GET https://benchmarkheaven.com/api/jevbench/<release>`. Record `label`, `sample`, `overnight.scored_utc`, and the SHA-256 of the response (it must equal the hash printed on `benchmarkheaven.com/jev-models`). Per system: `key`, `display`, `author`, `repo`, `underlying`, `licence`, `gpu`, `class`, `model_pin`, `rank`, `jevbench_score` (official Composite), `capability`, `axes` (I, C, S, K), `cost.usd_per_1000`, `speed.p50_s_adjusted`, `last_measured_on`. `not_measured[]` lists carried rows with `repo` and `reason`. Check the page for a newer release link before running.
5. Match each repo to a JevBench system by HF `base_model` against JevBench `repo` and `underlying`, then by name, then by author. The match table is hand-maintained in the script (`MATCHES`) so the evidence is explicit; the script prints candidate rows for any repo without an entry. Record quant, version, and hardware mismatches.
6. Jev-class eligibility is recomputed from the JSON: cost at most 2x and p50 at most 2x the Jev 1.13.0 row.
7. Watch list: JevBench rows with no GGUF in the collection, Gemma 4 31B first, then Gemma 4 12B, then other open weights that already ship a GGUF. For a new GGUF, read its header for `{arch}.decision.type`; without that key upstream llama-server returns 501 (doc-005).
8. Write the dated section: what changed, the tables, the analysis, one recommendation per model (adopt / try / skip).

## Fit method (RTX 3090, 24 GB)

Estimate = GGUF file size + f16 KV cache + 1 GB runtime overhead. KV cache = 2 (K and V) x block_count x head_count_kv x head size x context x 2 bytes. For Gemma 4 the per-layer `head_count_kv` list is averaged. Two contexts: 8k (the Quyet prompt cap, doc-005) and 32k. Verdict: fits below 20 GB, tight 20 to 23 GB, no above 23 GB. The mmproj file is excluded (text-only use). Encoder models (laya type) have an 8192 context cap in the header; their KV figure is nominal. Q8 KV cache or flash attention would roughly halve the KV term; the table does not assume either.

Reading the JevBench axes for a self-hosted target: Intelligence and Calibration (and their mean, Capability) describe the model. Speed and Cost were measured on the submitter's hardware, mostly H100 and A6000, with an estimated price, so they order the Composite but say little about a 3090. Compare on Capability first.

## Run 2026-10-05

Sources read 2026-10-05 board; JevBench JevBench v1.6.0 (1500 decisions self-hosted: 1200 sealed + 300 open; 92 ranked, roster 127). Scored 2026-10-05 09:06:16 UTC. JSON `https://benchmarkheaven.com/api/jevbench/v1.6.0` SHA-256 `b8560f6e00c45d5dfdf254954d2176b015aad279c741873c0ed7345673354866`. Collection last updated 2026-10-04, 8 repos.

**Changes since last run:** first run; this section is the baseline. Compared with doc-005 (written earlier the same day) the collection has two more repos: `Clef-Flash-GGUF` (9B) and `Bespoke-Nimble-9B-v3-GGUF` (9B).

#### Catalog

| repo | type | base model | params | license | quants (GB) | updated | JevBench match |
|---|---|---|---|---|---|---|---|
| [`ggml-org/Clef-GGUF`](https://huggingface.co/ggml-org/Clef-GGUF) | clef | Cloudflare/clef | 27B | apache-2.0 | BF16 54.1, Q4_K_M 19.2, Q8_0 28.7 | 2026-10-05 | [`clef`](https://benchmarkheaven.com/jev-models/clef) #43 |
| [`ggml-org/Clef-Flash-GGUF`](https://huggingface.co/ggml-org/Clef-Flash-GGUF) | clef | Cloudflare/clef-flash | 9.1B | apache-2.0 | BF16 18.2, Q4_K_M 6.5, Q8_0 9.7 | 2026-10-05 | [`clef-flash`](https://benchmarkheaven.com/jev-models/clef-flash) #21 |
| [`ggml-org/OpenJev-GGUF`](https://huggingface.co/ggml-org/OpenJev-GGUF) | openjev | openjev/openjev | 27B | cc-by-nc-4.0 | BF16 53.8, Q4_K_M 19.0, Q8_0 28.6 | 2026-10-01 | not measured |
| [`ggml-org/Laya-GGUF`](https://huggingface.co/ggml-org/Laya-GGUF) | laya | convaiinnovations/laya | 421M | apache-2.0 | BF16 0.8, Q8_0 0.4 | 2026-10-04 | [`laya`](https://benchmarkheaven.com/jev-models/laya) #84 |
| [`ggml-org/Julia-1-GGUF`](https://huggingface.co/ggml-org/Julia-1-GGUF) | laya | SupersonicLabs/Julia-1 | 144M | apache-2.0 | BF16 0.3, Q8_0 0.2 | 2026-10-01 | not measured |
| [`ggml-org/Kev-4B-GGUF`](https://huggingface.co/ggml-org/Kev-4B-GGUF) | kev | jaredpalmer/kev-4b | 4.2B | apache-2.0 | BF16 8.4, Q4_K_M 3.0, Q8_0 4.5 | 2026-10-01 | not measured |
| [`ggml-org/lev-GGUF`](https://huggingface.co/ggml-org/lev-GGUF) | lev | interfaze-ai/lev | 4.2B | apache-2.0 | BF16 8.4, Q4_K_M 3.0, Q8_0 4.5 | 2026-10-02 | [`lev`](https://benchmarkheaven.com/jev-models/lev) #14 |
| [`ggml-org/Bespoke-Nimble-9B-v3-GGUF`](https://huggingface.co/ggml-org/Bespoke-Nimble-9B-v3-GGUF) | nimble | bespokelabs/Bespoke-Nimble-9B-v3 | 9.0B | cc-by-nc-4.0 | BF16 17.9, Q4_K_M 6.3, Q8_0 9.5 | 2026-10-02 | [`nimble-9b`](https://benchmarkheaven.com/jev-models/nimble-9b) #33 |

#### JevBench scores for matched rows (Jev 1.13.0 reference first)

| system | I | C | S | K | Cap. | Composite | Rank | $/1k | p50 | Jev-class | measured | GPU |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [Jev 1.13.0 (API)](https://benchmarkheaven.com/jev-models/jev-1.13.0) | 62.4 | 90.6 | 91.5 | 54.7 | 76.5 | 71.1 | #2 | $0.0323 | 0.24 s | yes | 2026-10-01 | API |
| [Clef (Cloudflare, Qwen3.8-27B post-train with a joint schema head, multimodal, measured on text)](https://benchmarkheaven.com/jev-models/clef) | 59.1 | 91.6 | 83.4 | 28.1 | 75.3 | 16.8 | #43 | $0.2492 | 0.58 s | no | 2026-10-04 | H100 |
| [Clef-Flash (Cloudflare, Qwen3.5-9B post-train with a joint schema head, multimodal, measured on text)](https://benchmarkheaven.com/jev-models/clef-flash) | 42.2 | 85.5 | 88.4 | 46.8 | 63.8 | 36.6 | #21 | $0.0593 | 0.36 s | yes | 2026-10-04 | H100 |
| [Laya (Convai Innovations, ModernBERT-large 421M)](https://benchmarkheaven.com/jev-models/laya) | 1.8 | 63.2 | 73.3 | 84.9 | 32.5 | 0.0 | #84 | $0.0032 | 1.80 s | no | 2026-10-02 | cpu |
| [lev (Interfaze AI, Qwen3.5-4B + LoRA r32, label-token readout + candidate-path head, per-bucket temperatures)](https://benchmarkheaven.com/jev-models/lev) | 41.1 | 82.3 | 88.0 | 61.8 | 61.7 | 42.2 | #14 | $0.0188 | 0.35 s | yes | 2026-10-04 | H100 |
| [Bespoke Nimble 9B (Bespoke Labs)](https://benchmarkheaven.com/jev-models/nimble-9b) | 43.1 | 69.9 | 86.1 | 36.8 | 56.5 | 21.1 | #33 | $0.1283 | 0.44 s | no | 2026-10-02 | A6000 |

Jev-class "no" for Clef and Nimble comes from the cost axis (H100 and A6000 estimated prices), not from Intelligence. Laya's 1.80 s p50 was measured on a shared CPU host.

#### Match evidence

- [`ggml-org/Clef-GGUF`](https://huggingface.co/ggml-org/Clef-GGUF): [`clef`](https://benchmarkheaven.com/jev-models/clef). JevBench repo = HF Cloudflare/clef, underlying Qwen3.8-27B; GGUF base_model Cloudflare/clef. Measured BF16 on H100, text only; GGUF quants differ.
- [`ggml-org/Clef-Flash-GGUF`](https://huggingface.co/ggml-org/Clef-Flash-GGUF): [`clef-flash`](https://benchmarkheaven.com/jev-models/clef-flash). JevBench repo = HF Cloudflare/clef-flash, underlying Qwen3.5-9B; GGUF base_model Cloudflare/clef-flash. Measured BF16 on H100, text only.
- [`ggml-org/OpenJev-GGUF`](https://huggingface.co/ggml-org/OpenJev-GGUF): none. No row. JevBench 'OpenJev (thinking, BF16)' is razorback16/openjev on diffusiongemma-26b-a4b, not openjev/openjev (Qwen3.8-27B). 'SemIf, formerly OpenJev' is a Qwen3.5-4B model. Neither is this GGUF.
- [`ggml-org/Laya-GGUF`](https://huggingface.co/ggml-org/Laya-GGUF): [`laya`](https://benchmarkheaven.com/jev-models/laya). JevBench repo = HF convaiinnovations/laya (English root, ModernBERT-large 421M); GGUF base_model convaiinnovations/laya. Measured on CPU. 'Laya multilingual' and 'Laya typed-decisions' are other checkpoints in the same repo, not this GGUF.
- [`ggml-org/Julia-1-GGUF`](https://huggingface.co/ggml-org/Julia-1-GGUF): none. No row. No JevBench system names SupersonicLabs or Julia; not in not_measured either.
- [`ggml-org/Kev-4B-GGUF`](https://huggingface.co/ggml-org/Kev-4B-GGUF): none. No clean row. JevBench 'kev 4B (research preview)' is jaredpalmer/kev-4b on Qwen3-4B-Base with a learned pointer head. The GGUF header says arch qwen35 (Qwen3.5) and HF base_model jaredpalmer/kev-4b; the announcement states Qwen3.5-4B-Base. The row is an earlier Kev generation, not a measurement of this GGUF.
- [`ggml-org/lev-GGUF`](https://huggingface.co/ggml-org/lev-GGUF): [`lev`](https://benchmarkheaven.com/jev-models/lev). JevBench repo = HF interfaze-ai/lev, pinned 7bdc748, underlying Qwen3.5-4B + LoRA r32; GGUF base_model interfaze-ai/lev. Measured BF16 on H100.
- [`ggml-org/Bespoke-Nimble-9B-v3-GGUF`](https://huggingface.co/ggml-org/Bespoke-Nimble-9B-v3-GGUF): [`nimble-9b`](https://benchmarkheaven.com/jev-models/nimble-9b). JevBench 'Bespoke Nimble 9B' = bespokelabs/Bespoke-Nimble-9B LoRA merged into Qwen3.5-9B; GGUF base_model bespokelabs/Bespoke-Nimble-9B-v3. Version (v3) not stated on the JevBench row. Measured on A6000.

#### RTX 3090 fit (24 GB; weights + f16 KV cache + 1 GB; text only, no mmproj)

| repo | quant | weights GB | KV @8k GB | KV @32k GB | total @8k | total @32k | verdict |
|---|---|---|---|---|---|---|---|
| [`Clef-GGUF`](https://huggingface.co/ggml-org/Clef-GGUF/blob/main/Clef-BF16.gguf) | BF16 | 54.1 | 2.1 | 8.6 | 57.2 | 63.7 | no / no |
| [`Clef-GGUF`](https://huggingface.co/ggml-org/Clef-GGUF/blob/main/Clef-Q4_K_M.gguf) | Q4_K_M | 19.2 | 2.1 | 8.6 | 22.4 | 28.8 | tight / no |
| [`Clef-GGUF`](https://huggingface.co/ggml-org/Clef-GGUF/blob/main/Clef-Q8_0.gguf) | Q8_0 | 28.7 | 2.1 | 8.6 | 31.9 | 38.3 | no / no |
| [`Clef-Flash-GGUF`](https://huggingface.co/ggml-org/Clef-Flash-GGUF/blob/main/Clef-Flash-BF16.gguf) | BF16 | 18.2 | 1.1 | 4.3 | 20.2 | 23.5 | tight / no |
| [`Clef-Flash-GGUF`](https://huggingface.co/ggml-org/Clef-Flash-GGUF/blob/main/Clef-Flash-Q4_K_M.gguf) | Q4_K_M | 6.5 | 1.1 | 4.3 | 8.6 | 11.8 | fits / fits |
| [`Clef-Flash-GGUF`](https://huggingface.co/ggml-org/Clef-Flash-GGUF/blob/main/Clef-Flash-Q8_0.gguf) | Q8_0 | 9.7 | 1.1 | 4.3 | 11.7 | 15.0 | fits / fits |
| [`OpenJev-GGUF`](https://huggingface.co/ggml-org/OpenJev-GGUF/blob/main/OpenJev-BF16.gguf) | BF16 | 53.8 | 2.1 | 8.6 | 57.0 | 63.4 | no / no |
| [`OpenJev-GGUF`](https://huggingface.co/ggml-org/OpenJev-GGUF/blob/main/OpenJev-Q4_K_M.gguf) | Q4_K_M | 19.0 | 2.1 | 8.6 | 22.1 | 28.6 | tight / no |
| [`OpenJev-GGUF`](https://huggingface.co/ggml-org/OpenJev-GGUF/blob/main/OpenJev-Q8_0.gguf) | Q8_0 | 28.6 | 2.1 | 8.6 | 31.7 | 38.2 | no / no |
| [`Laya-GGUF`](https://huggingface.co/ggml-org/Laya-GGUF/blob/main/Laya-BF16.gguf) | BF16 | 0.8 | 1.0 | 4.0 | 2.9 | 5.9 | fits / fits |
| [`Laya-GGUF`](https://huggingface.co/ggml-org/Laya-GGUF/blob/main/Laya-Q8_0.gguf) | Q8_0 | 0.4 | 1.0 | 4.0 | 2.5 | 5.5 | fits / fits |
| [`Julia-1-GGUF`](https://huggingface.co/ggml-org/Julia-1-GGUF/blob/main/Julia-1-BF16.gguf) | BF16 | 0.3 | 0.3 | 1.2 | 1.6 | 2.5 | fits / fits |
| [`Julia-1-GGUF`](https://huggingface.co/ggml-org/Julia-1-GGUF/blob/main/Julia-1-Q8_0.gguf) | Q8_0 | 0.2 | 0.3 | 1.2 | 1.5 | 2.4 | fits / fits |
| [`Kev-4B-GGUF`](https://huggingface.co/ggml-org/Kev-4B-GGUF/blob/main/Kev-4B-BF16.gguf) | BF16 | 8.4 | 1.1 | 4.3 | 10.5 | 13.7 | fits / fits |
| [`Kev-4B-GGUF`](https://huggingface.co/ggml-org/Kev-4B-GGUF/blob/main/Kev-4B-Q4_K_M.gguf) | Q4_K_M | 3.0 | 1.1 | 4.3 | 5.1 | 8.3 | fits / fits |
| [`Kev-4B-GGUF`](https://huggingface.co/ggml-org/Kev-4B-GGUF/blob/main/Kev-4B-Q8_0.gguf) | Q8_0 | 4.5 | 1.1 | 4.3 | 6.6 | 9.8 | fits / fits |
| [`lev-GGUF`](https://huggingface.co/ggml-org/lev-GGUF/blob/main/lev-BF16.gguf) | BF16 | 8.4 | 1.1 | 4.3 | 10.5 | 13.7 | fits / fits |
| [`lev-GGUF`](https://huggingface.co/ggml-org/lev-GGUF/blob/main/lev-Q4_K_M.gguf) | Q4_K_M | 3.0 | 1.1 | 4.3 | 5.1 | 8.3 | fits / fits |
| [`lev-GGUF`](https://huggingface.co/ggml-org/lev-GGUF/blob/main/lev-Q8_0.gguf) | Q8_0 | 4.5 | 1.1 | 4.3 | 6.6 | 9.8 | fits / fits |
| [`Bespoke-Nimble-9B-v3-GGUF`](https://huggingface.co/ggml-org/Bespoke-Nimble-9B-v3-GGUF/blob/main/Bespoke-Nimble-9B-v3-BF16.gguf) | BF16 | 17.9 | 1.1 | 4.3 | 20.0 | 23.2 | fits / no |
| [`Bespoke-Nimble-9B-v3-GGUF`](https://huggingface.co/ggml-org/Bespoke-Nimble-9B-v3-GGUF/blob/main/Bespoke-Nimble-9B-v3-Q4_K_M.gguf) | Q4_K_M | 6.3 | 1.1 | 4.3 | 8.4 | 11.6 | fits / fits |
| [`Bespoke-Nimble-9B-v3-GGUF`](https://huggingface.co/ggml-org/Bespoke-Nimble-9B-v3-GGUF/blob/main/Bespoke-Nimble-9B-v3-Q8_0.gguf) | Q8_0 | 9.5 | 1.1 | 4.3 | 11.6 | 14.8 | fits / fits |

#### GGUF header facts (probe quant)

- [`ggml-org/Clef-GGUF`](https://huggingface.co/ggml-org/Clef-GGUF) (Clef-Q8_0.gguf): arch `clef`; decision {'type': 'clef', 'routing_block_count': 2, 'block_count': 4, 'head_count': 16}; {'block_count': 64, 'context_length': 262144, 'embedding_length': 5120, 'attention.head_count': 24, 'attention.head_count_kv': 4, 'attention.layer_norm_rms_epsilon': 9.999999974752427e-07, 'attention.key_length': 256, 'attention.value_length': 256}
- [`ggml-org/Clef-Flash-GGUF`](https://huggingface.co/ggml-org/Clef-Flash-GGUF) (Clef-Flash-Q8_0.gguf): arch `clef`; decision {'type': 'clef', 'routing_block_count': 2, 'block_count': 4, 'head_count': 16}; {'block_count': 32, 'context_length': 262144, 'embedding_length': 4096, 'attention.head_count': 16, 'attention.head_count_kv': 4, 'attention.layer_norm_rms_epsilon': 9.999999974752427e-07, 'attention.key_length': 256, 'attention.value_length': 256}
- [`ggml-org/OpenJev-GGUF`](https://huggingface.co/ggml-org/OpenJev-GGUF) (OpenJev-Q8_0.gguf): arch `qwen35`; decision {'type': 'openjev', 'temperature.choice': 0.8500000238418579, 'temperature.score': 0.8500000238418579, 'temperature.noul': 1.5547128915786743}; {'block_count': 64, 'context_length': 262144, 'embedding_length': 5120, 'attention.head_count': 24, 'attention.head_count_kv': 4, 'attention.layer_norm_rms_epsilon': 9.999999974752427e-07, 'attention.key_length': 256, 'attention.value_length': 256}
- [`ggml-org/Laya-GGUF`](https://huggingface.co/ggml-org/Laya-GGUF) (Laya-Q8_0.gguf): arch `modern-bert`; decision {'type': 'laya', 'block_count': 2, 'max_head_tokens': 192, 'temperature.choice': 1.6369030475616455, 'temperature.score': 1.2514300346374512, 'temperature.noul': 1.983399510383606, 'temperature.choice.3_5': 1.7601518630981445, 'temperature.choice.6_10': 1.0000158548355103, 'temperature.score.3_5': 1.2514300346374512, 'temperature.noul.2': 1.983399510383606, 'temperature.choice.11': 0.10058280825614929, 'temperature.choice.2': 1.9063563346862793}; {'block_count': 30, 'context_length': 8192, 'embedding_length': 1024, 'attention.head_count': 16, 'attention.layer_norm_rms_epsilon': 9.999999747378752e-06}
- [`ggml-org/Julia-1-GGUF`](https://huggingface.co/ggml-org/Julia-1-GGUF) (Julia-1-Q8_0.gguf): arch `modern-bert`; decision {'type': 'laya', 'block_count': 2, 'max_head_tokens': 256}; {'block_count': 24, 'context_length': 8192, 'embedding_length': 384, 'attention.head_count': 6, 'attention.layer_norm_rms_epsilon': 9.999999747378752e-06}
- [`ggml-org/Kev-4B-GGUF`](https://huggingface.co/ggml-org/Kev-4B-GGUF) (Kev-4B-Q8_0.gguf): arch `qwen35`; decision {'type': 'kev', 'temperature.choice': 2.406049966812134, 'temperature.score': 2.406049966812134, 'temperature.noul': 2.406049966812134}; {'block_count': 32, 'context_length': 262144, 'embedding_length': 2560, 'attention.head_count': 16, 'attention.head_count_kv': 4, 'attention.layer_norm_rms_epsilon': 9.999999974752427e-07, 'attention.key_length': 256, 'attention.value_length': 256, 'embedding_length_out': 512}
- [`ggml-org/lev-GGUF`](https://huggingface.co/ggml-org/lev-GGUF) (lev-Q8_0.gguf): arch `qwen35`; decision {'type': 'lev', 'temperature.noul': 2.3332931995391846, 'temperature.score': 2.803323745727539, 'temperature.choice': 1.7666659355163574, 'temperature.choice.small': 1.7897834777832031, 'temperature.choice.mid': 1.608568549156189, 'temperature.choice.large': 1.6641112565994263}; {'block_count': 32, 'context_length': 262144, 'embedding_length': 2560, 'attention.head_count': 16, 'attention.head_count_kv': 4, 'attention.layer_norm_rms_epsilon': 9.999999974752427e-07, 'attention.key_length': 256, 'attention.value_length': 256}
- [`ggml-org/Bespoke-Nimble-9B-v3-GGUF`](https://huggingface.co/ggml-org/Bespoke-Nimble-9B-v3-GGUF) (Bespoke-Nimble-9B-v3-Q8_0.gguf): arch `qwen35`; decision {'type': 'nimble'}; {'block_count': 32, 'context_length': 262144, 'embedding_length': 4096, 'attention.head_count': 16, 'attention.head_count_kv': 4, 'attention.layer_norm_rms_epsilon': 9.999999974752427e-07, 'attention.key_length': 256, 'attention.value_length': 256}

#### Watch list: JevBench systems without a collection GGUF

| system | base / underlying | licence | repo | I | C | S | K | Cap. | Composite | Rank | $/1k | p50 | Jev-class |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [Quyet-1.0-Large (Chinh Nguyen, Gemma-4-31B decoder, option-letter logits)](https://benchmarkheaven.com/jev-models) | google/gemma-4-31B-it | apache-2.0 | https://huggingface.co/chinhnc/Quyet-1.0-Large | 73.4 | 90.0 | 86.9 | 50.5 | 81.7 | 71.4 | #1 | $0.0445 | 0.38 s | yes |
| [deck-31B (krishna765, frozen Gemma-4-31B-it, TorchAO FP8 dynamic)](https://benchmarkheaven.com/jev-models) | None | None | https://github.com/krishna-gogineni-765/deck31b | 73.0 | 82.2 | 86.7 | 49.9 | 77.6 | 69.3 | #5 | $0.0468 | 0.40 s | yes |
| [torchcast-decision-12b (Torchcast AI, Gemma-4-12B fine-tune, option-letter logprob readout)](https://benchmarkheaven.com/jev-models) | google/gemma-4-12B-it | cc-by-nc-4.0 | https://huggingface.co/torchcast-ai/torchcast-decision-12b | 60.5 | 82.9 | 91.7 | 56.4 | 71.7 | 69.9 | #4 | $0.0285 | 0.22 s | yes |
| [Winnow-12B Q8](https://benchmarkheaven.com/jev-models/winnow-12b) | google/gemma-4-12B-it LoRA fine-tune, merged and exported as Q8_0 GGUF | Apache-2.0, including the applicable Gemma 4 base/derivative licence terms | https://huggingface.co/EldanRing/Winnow-12B | 59.5 | 83.0 | 86.7 | 56.6 | 71.2 | 68.9 | #6 | $0.0281 | 0.38 s | yes |
| [Cygnet (blockbrain, frozen Gemma-4-12B-it)](https://benchmarkheaven.com/jev-models/cygnet) | None | shim MIT; weights Apache-2.0 with Google's Gemma Prohibited Use Policy | https://github.com/blockbrain-ai/cygnet-recipe | 54.8 | 87.0 | 91.8 | 56.4 | 70.9 | 68.6 | #7 | $0.0283 | 0.22 s | yes |
| [Jev-Omni (akhilaaa3, Gemma-4-12B merged)](https://benchmarkheaven.com/jev-models/jev-omni) | google/gemma-4-12B-it fine-tuned and merged, with a trained 256-way decision hea | Apache-2.0, following Gemma 4; dataset rights stated separately by the author | https://huggingface.co/akhilaaa3/Jev-Omni | 55.5 | 87.0 | 85.4 | 56.1 | 71.3 | 67.7 | #8 | $0.0292 | 0.46 s | yes |
| [Autoloops – Gemma 4 31B IT](https://benchmarkheaven.com/jev-models/kushal-gemma4-31b-it-autoloops) | not measured on v1.6.0 | | https://benchmarkheaven.com/jev-models/kushal-gemma4-31b-it-autoloops | Not measured on the v1.6.0 pool. |
| [Quyet-1.0-Medium (Chinh Nguyen, Qwen3.5-4B decoder, option-letter logits)](https://benchmarkheaven.com/jev-models) | Qwen/Qwen3.5-4B | apache-2.0 | https://huggingface.co/chinhnc/Quyet-1.0-Medium | 41.7 | 76.8 | 89.5 | 63.4 | 59.2 | 43.6 | #13 | $0.0166 | 0.30 s | yes |
| [decider-4b v2 (Mapika)](https://benchmarkheaven.com/jev-models/decider-4b-v2) | None | Apache-2.0 (package and weights) | https://github.com/Mapika/decider | 40.1 | 89.6 | 91.8 | 64.5 | 64.9 | 41.2 | #17 | $0.0152 | 0.20 s | yes |
| [JevK5 v0.3 (4B)](https://benchmarkheaven.com/jev-models/jevk5-v0.3-4b) | None | not recorded | https://huggingface.co/alibiserikbay/JevK5 | 38.5 | 89.9 | 93.9 | 63.1 | 64.2 | 37.4 | #18 | $0.0170 | 0.19 s | yes |
| [OpenSourceJev (Qwen3.5-4B Q4_K_M, native llama.cpp)](https://benchmarkheaven.com/jev-models/opensourcejev-qwen35-4b-q4km) | None | MIT (repository code); Apache-2.0 (Qwen/Qwen3.5-4B base and unsloth/Qwen3.5-4B-GGUF Q4_K_M conversion) | https://github.com/sabeel111/OpenSourceJev | 23.2 | 73.9 | 77.1 | 69.1 | 48.6 | 10.3 | #52 | $0.0107 | 0.74 s | no |
| [Plumb-4B (crh225, JevK5 v0.2 + LoRA)](https://benchmarkheaven.com/jev-models/plumb-4b) | None | not recorded | https://huggingface.co/crh225/plumb-4b | 43.0 | 87.9 | 93.8 | 63.1 | 65.4 | 48.3 | #10 | $0.0170 | 0.19 s | yes |
| [OpenJev (thinking, BF16)](https://benchmarkheaven.com/jev-models/openjev-thinking) | google/diffusiongemma-26b-a4b-it, BF16; OpenJev think=512 | Apache-2.0 | https://github.com/razorback16/openjev | 70.3 | 81.4 | 72.6 | 28.5 | 75.9 | 17.3 | #40 | $0.2415 | 1.86 s | no |

Watch list notes:

- **Winnow-12B Q8** (rank 6, Capability 71.2, Apache-2.0) already ships a Q8_0 GGUF (12.7 GB) and an NVFP4 GGUF (8.2 GB) at [`EldanRing/Winnow-12B`](https://huggingface.co/EldanRing/Winnow-12B) ([JevBench page](https://benchmarkheaven.com/jev-models/winnow-12b)). The Q8_0 header read on 2026-10-05 has **no `gemma4.decision.type`** and no temperature keys, so upstream llama-server would return 501. Its `/v1/systemone` comes from the author's llama.cpp fork (`github.com/EldanRing/winnow-inference`, pinned revision plus a native typed-decision patch). The README reports 15.0 GiB peak VRAM for Q8 with 64k context. This is the closest thing to a Gemma 4 model that fits the 3090 today; the gap is upstream metadata, not weights.
- **Quyet-1.0-Large** (rank 1, Gemma 4 31B) and **deck-31B** (rank 5) have no compatible GGUF (doc-005 covers the Quyet header). A 31B Q4_K_M is about 19 GB, which is tight on a 3090 even at 8k context (see the Clef and OpenJev rows). A Gemma 4 31B GGUF, when it appears, is a 3090 fit only at Q4 with short context; the 12B Gemma 4 rows (Winnow, torchcast, Cygnet, Jev-Omni, ranks 4 to 8, Capability 70.9 to 71.7) are the realistic target.
- **torchcast-decision-12b** is CC-BY-NC-4.0. Cygnet and Jev-Omni publish recipes and safetensors, no GGUF found in the JevBench repo links; not checked further this run.
- **OpenSourceJev** (rank 52) describes itself as "Qwen3.5-4B Q4_K_M, native llama.cpp" but scores far below lev; listed only because it claims upstream compatibility.
- JevK5 v0.3 (rank 18), Plumb-4B (rank 10), decider-4b v2 (rank 17) are Qwen3.5-4B systems with their own servers; none has a GGUF in the collection.

#### Analysis and recommendations

Tradeoffs across the eight collection models:

- Only three repos are measured on v1.6.0 with a defensible match and a usable score: lev (rank 14), Clef-Flash (rank 21), Clef (rank 43). Nimble (rank 33) is measured but non-commercial and poorly calibrated (C 69.9). Laya is measured but floored by noul abstention (I 1.8). OpenJev, Julia-1, and this generation of Kev-4B are unmeasured.
- Capability: Clef 75.3 (close to Jev 76.5) > Clef-Flash 63.8 > lev 61.7 > Nimble 56.5 > Laya 32.5. Intelligence: Clef 59.1 > Nimble 43.1 > Clef-Flash 42.2 > lev 41.1. Calibration: Clef 91.6 > Clef-Flash 85.5 > lev 82.3.
- VRAM: everything at or below 9B fits with room at Q8_0. The two 27B models fit only at Q4_K_M with 8k context (22 GB, tight) and not at 32k. Both 27B scores were measured at BF16, so a Q4 run would also be a quant mismatch.
- Licence: Clef, Clef-Flash, lev, Kev-4B, Laya, Julia-1 are Apache-2.0. OpenJev and Nimble are CC-BY-NC-4.0.
- Mechanism (doc-005): clef type answers all questions jointly and the server then serves only `/v1/systemone`; lev supports up to 255 options with per-bucket temperatures; kev is text-only with 255 options; laya truncates to `max_head_tokens` (192 for Laya, 256 for Julia-1) and an 8k context.

Recommendation per model (adopt = install on saturn now, try = install when a slot is free, skip = not now):

| model | verdict | reason |
|---|---|---|
| [`lev-GGUF`](https://huggingface.co/ggml-org/lev-GGUF) Q8_0 | **adopt** | best measured Apache model that fits with room (4.5 GB); rank 14, Jev-class; 255 options; good first probe target for NUMP-016 |
| [`Clef-Flash-GGUF`](https://huggingface.co/ggml-org/Clef-Flash-GGUF) Q8_0 | **try** | Capability 63.8 and Calibration 85.5 beat lev; 9.7 GB fits; cost: joint answering and the endpoint lock-in of the clef type, and the server must be dedicated to it |
| [`Clef-GGUF`](https://huggingface.co/ggml-org/Clef-GGUF) Q4_K_M | **try later** | the only Apache model near Jev's Capability (75.3); tight on the 3090 at 8k context, no at 32k; measured at BF16, so expect some loss at Q4 |
| [`Kev-4B-GGUF`](https://huggingface.co/ggml-org/Kev-4B-GGUF) Q8_0 | **try** | unmeasured for this Qwen3.5 generation (the board row is the Qwen3 predecessor, I 19.5); Apache, 4.5 GB; worth one probe alongside lev since it is the other small native option |
| [`Laya-GGUF`](https://huggingface.co/ggml-org/Laya-GGUF) Q8_0 | **skip for quality, keep as test double** | I 1.8 on JevBench (noul abstention); but 0.4 GB and milliseconds, useful as an offline fixture for NUMP-007 tests |
| [`Julia-1-GGUF`](https://huggingface.co/ggml-org/Julia-1-GGUF) | **skip** | unmeasured, 144M, multilingual focus; same role as Laya if needed |
| [`OpenJev-GGUF`](https://huggingface.co/ggml-org/OpenJev-GGUF) | **skip** | CC-BY-NC-4.0, unmeasured, 27B tight at Q4 |
| [`Bespoke-Nimble-9B-v3-GGUF`](https://huggingface.co/ggml-org/Bespoke-Nimble-9B-v3-GGUF) | **skip** | CC-BY-NC-4.0, Calibration 69.9, below lev on Capability despite twice the size |

Watch item for the next run: an upstream-compatible Gemma 4 12B GGUF (Winnow with decision metadata, or a ggml-org conversion of torchcast, Cygnet, or Jev-Omni) would outrank every collection model that fits the 3090 by about 10 Capability points and should become the adopt candidate.
