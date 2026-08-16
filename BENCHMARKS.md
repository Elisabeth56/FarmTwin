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
