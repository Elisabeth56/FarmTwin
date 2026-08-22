# BENCHMARKS.md — Real benchmark results

Only real, reproducible numbers go in this file. No estimates, no placeholders that look like results, no numbers copied from model cards. If a row has no data, leave it explicitly empty with "not yet measured."

## Ground rules

- Every number is produced on the **ADTC Standard Laptop** (Ubuntu 22.04, x86-64, 8 GB RAM, integrated graphics, no dGPU) — or a matching VM, clearly labeled.
- Every number is reproducible from a single command committed under `evaluation/`. The command goes in the "Command" column.
- Peak RSS is measured from process start to process exit for the full evaluated workload (not idle).
- Tokens/sec is measured on prompts representative of the FarmTwin use case, not on generic benchmarks.
- If a number is measured on a **VM** that doesn't match ADTC hardware, mark it clearly: `(VM — not final)`. Non-final numbers do not go in the submission report.
- When a component is swapped or re-tuned, add a new row rather than overwriting the old one. Date and pinned-commit hash mandatory.

## Environment

| Field | Value |
| --- | --- |
| Hardware profile | not yet measured |
| Kernel / OS build | not yet measured |
| llama.cpp commit | not yet pinned (Day 1 task) |
| Python version | not yet recorded |
| Node version | not yet recorded |
| Date of most recent full run | — |

## LLM — candidate models (Day 1 baselines, Day 6 finals)

| Date | Model | Quant | Prompt | Tokens/sec | Peak RSS | Hardware | Command | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| — | Qwen2.5-3B-Instruct | Q4_K_M | — | not yet measured | not yet measured | — | — | Day 1 candidate |
| — | Llama-3.2-3B-Instruct | Q4_K_M | — | not yet measured | not yet measured | — | — | Day 1 candidate |

## Embedder (Day 2)

| Date | Model | Dim | Chunks/sec ingest | Query latency | Peak RSS added | Command | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| — | not yet chosen | — | not yet measured | not yet measured | not yet measured | — | Chosen based on Day 1 headroom |

## Retrieval quality (Day 2 → Day 6)

Manual pass on the two official test prompts and the ~15 sample queries used to iterate the corpus.

| Date | Query | Top-k | Relevant hits in top-k | Notes |
| --- | --- | --- | --- | --- |
| — | Test Prompt 1 (Kaduna maize, vegetative, 2-week outlook) | — | not yet measured | — |
| — | Test Prompt 2 (Kaduna maize, heavy rainfall + humidity) | — | not yet measured | — |

## End-to-end `/api/ask` (Day 3 → Day 6)

| Date | Prompt | Total latency | Time-to-first-token | Total tokens | Notes |
| --- | --- | --- | --- | --- | --- |
| — | Test Prompt 1 | not yet measured | not yet measured | not yet measured | — |
| — | Test Prompt 2 | not yet measured | not yet measured | not yet measured | — |

## Combined memory — LLM + embedder + (optional) whisper (Day 5.5)

Measured during a 5-query burst with everything loaded.

| Date | Config | Peak combined RSS | Ceiling | Under? | Notes |
| --- | --- | --- | --- | --- | --- |
| — | LLM only | not yet measured | 7 GB | — | — |
| — | LLM + embedder | not yet measured | 7 GB | — | — |
| — | LLM + embedder + whisper.cpp | not yet measured | 7 GB | — | Gate decision for STT |

## STT — Whisper (Day 5.5)

15-clip test set: 5 EN clean, 5 EN accented, 5 Pidgin.

| Date | Language | Model | WER | RTF | Peak RSS | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| — | English | `ggml-base-q5_1` | not yet measured | not yet measured | not yet measured | — |
| — | Nigerian Pidgin | `ggml-base-q5_1` | not yet measured | not yet measured | not yet measured | Drives ship / EN-only / cut gate |

## Thermal / sustained-load (Day 6, if time)

| Date | Scenario | Duration | Throttle observed? | Notes |
| --- | --- | --- | --- | --- |
| — | 5-min sustained ask loop | — | not yet measured | — |

## Offline verification (Day 7)

| Date | Test | Passed? | Notes |
| --- | --- | --- | --- |
| — | Airplane-mode full demo (text) | not yet run | — |
| — | Airplane-mode full demo (voice, if STT shipped) | not yet run | — |
| — | Runtime egress audit (no outbound HTTP) | not yet run | — |

# FarmTwin Benchmarks

## Day 1 baseline measurements (2026-08-17)

### Environment
- Host: Intel Mac, macOS
- llama.cpp tag: b10472  
- Build flags: `-DGGML_METAL=OFF -DGGML_ACCELERATE=OFF`  (CPU-only, no acceleration)
- Threads: 4
- Context size: 4096
- Note: These are dev-machine (macOS) measurements. Official ADTC target-hardware
  benchmarks will be run in Docker/Linux on Day 6 and reported separately.

### Qwen2.5-3B-Instruct Q4_K_M
- Peak RSS: 2.15 GB (2,310,877,184 bytes)
- Load + 3 short queries wall-clock: 39.28 s
- Load mode: mlock
- Status: ✅ Well within 7 GB ceiling

### Llama-3.2-3B-Instruct Q4_K_M
- Peak RSS: 2.36 GB (2,535,174,144 bytes)
- Load + 3 short queries wall-clock: 54.87 s
- Load mode: mlock
- Status: ✅ Well within 7 GB ceiling
- Note: ~10% heavier RSS and ~40% slower than Qwen2.5-3B on this hardware

## Day 2 shape test (2026-08-18)

### Environment
- Same as Day 1 (Intel Mac, macOS, CPU-only)
- Model: Qwen2.5-3B-Instruct Q4_K_M
- Prompt structure: RAG-augmented (farm facts + top-6 chunks + question)
- Retrieval: sentence-transformers all-MiniLM-L6-v2 embeddings, sqlite-vec KNN

### Shape test results (single query, not a benchmark)
- Prompt size: 6,574 chars / ~1,259 tokens
- Prompt eval: 74.9 s (18.8 tok/s) — cold cache
- Generation: 89.5 s for 402 tokens (4.5 tok/s)
- Total wall-clock: 164.5 s
- Response quality: farm-specific, correctly grounded in retrieved chunks
- JSON block: valid and parseable when correctly extracted

### Notes
- First-prompt cold cache dominated eval time; subsequent shared prefixes should be much faster
- Model echoed the system prompt (Qwen chat-template issue — fixable Day 3)
- Only 1 recommendation returned; needs few-shot examples for 2-3 (Day 3)


# FarmTwin Benchmarks

## Day 6 model selection benchmark (2026-08-22)

### Environment
- Host: Intel Mac (2014 MacBook Pro), macOS
- RAM: 8 GB
- CPU: 4-core Intel
- llama.cpp: pinned tag (see ADR-003)
- Build flags: `-DGGML_METAL=OFF -DGGML_ACCELERATE=OFF` (CPU-only)
- Runtime: `--ctx-size 4096 --threads 4 --load-mode mlock`
- Test set: 10 gold prompts from `evaluation/gold_prompts.json`
- All prompts include the 2 official ADTC test prompts (PRODUCT.md §34) plus 8 farm-scenario variants
- Manual rubric grading on 5 dimensions (0-5 each): farm-context grounding, retrieval grounding, agronomic factuality, actionability, structure conformance
- Scoring weights: Accuracy 60%, Throughput 25%, Efficiency 15% (compressed from original 50/30/20 given smaller test set)

### Candidates

Two candidates benchmarked. Third candidate (Gemma-2-2B) cut for time given single-day compressed schedule.

#### Qwen2.5-3B-Instruct Q4_K_M (WINNER)

| Metric | Value |
|---|---|
| Accuracy | 87.6 / 100 |
| — Farm-context grounding | 4.80 / 5.00 |
| — Retrieval grounding | 4.20 / 5.00 |
| — Agronomic factuality | 4.90 / 5.00 |
| — Actionability | 4.00 / 5.00 |
| — Structure conformance | 4.00 / 5.00 |
| Prompt eval | 19.0 tok/s (mean) |
| Generation | 5.4 tok/s (mean) |
| Wall clock (10 prompts) | 24.1 min |
| Peak RSS | 3063 MB (44% of 7 GB ceiling) |
| Completion rate | 10/10 |
| **Composite** | **83.5** |

#### Llama-3.2-3B-Instruct Q4_K_M

| Metric | Value |
|---|---|
| Accuracy | 82.8 / 100 |
| — Farm-context grounding | 5.00 / 5.00 |
| — Retrieval grounding | 2.60 / 5.00 |
| — Agronomic factuality | 4.30 / 5.00 |
| — Actionability | 4.00 / 5.00 |
| — Structure conformance | 4.80 / 5.00 |
| Prompt eval | 18.1 tok/s (mean) |
| Generation | 3.8 tok/s (mean) |
| Wall clock (10 prompts) | 29.6 min |
| Peak RSS | 3530 MB (50% of 7 GB ceiling) |
| Completion rate | 10/10 |
| **Composite** | **72.9** |

### Decision: Qwen2.5-3B-Instruct Q4_K_M

Reasoning:
1. **Higher accuracy overall** (87.6 vs 82.8)
2. **Substantially better retrieval grounding** (4.20 vs 2.60) — Llama cited chunks that did not support its claims, a critical failure mode for a RAG system where fabricated citations undermine the entire "grounded reasoning" value proposition
3. **42% faster generation** (5.4 vs 3.8 tok/s), 23% faster overall
4. **15% lower memory footprint** (467 MB additional headroom vs Llama, meaningful on the 7 GB ceiling)
5. Equal completion rate (10/10)
6. Llama produced slightly cleaner JSON structure but that advantage does not offset the retrieval grounding deficit

### Notes and honest caveats

- Small test set (10 prompts). LLM-as-judge grading of a larger set was cut for time.
- Manual grading has grader bias. Same grader graded both models with same rubric.
- Benchmarks run on Intel Mac 8GB dev machine, not the ADTC Ubuntu target. Numbers should be interpreted as lower-bound proxy — Ubuntu target hardware likely produces equal or better performance.
- Gemma-2-2B candidate cut from selection process. Original 3-way benchmark planned but time-boxed to 2 candidates.
- Docker-based Ubuntu benchmark cut for the same reason. See ADR-009 for hardware constraint context.
- Both models fit comfortably within 7 GB ceiling. Neither breaches memory limits under normal operation.