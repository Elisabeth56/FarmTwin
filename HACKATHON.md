# HACKATHON.md — Africa Deep Tech Challenge 2026 Constraints

FarmTwin is being built for the **Africa Deep Tech Challenge 2026 — The Laptop LLM Challenge**. This document freezes the hackathon rules that shape every engineering decision. When a decision trades off against a rule below, log it in `DECISIONS.md`.

## 1. Domain

FarmTwin's declared domain is **Agriculture**: crop, livestock, weather, and market advisory for farmers and extension officers.

Other published ADTC domains (for reference only — we are not building for them):

- Math & Scientific Reasoning
- Healthcare & Medical
- Creative Writing
- Coding Assistants
- Corporate / Enterprise
- Autonomous AI Agents

Each team selects **one** primary domain. FarmTwin's is Agriculture.

## 2. What must be built

A working, end-to-end, **on-device Language Model** application that:

- Runs without cloud dependencies on the ADTC Standard Laptop.
- Addresses the chosen problem domain (Agriculture, for us).
- Can be evaluated against the ADTC standardized benchmarks for that domain.

## 3. Reference hardware — ADTC Standard Laptop

Participants may develop on any hardware, but final benchmarks and audits are reported against this profile.

| Component | ADTC Standard Laptop |
| --- | --- |
| CPU | Intel Core i5 10th–12th gen OR AMD Ryzen 5 3000–5000 (x86-64) |
| RAM | **8 GB DDR4** |
| Graphics | Integrated only (Intel UHD / Iris Xe or AMD Radeon integrated). **No discrete GPU.** |
| Storage | 256 GB SSD |
| OS (reference) | **Ubuntu 22.04 LTS** |
| Representative price | $400–$500 new / $150–$250 refurbished |

## 4. Hard memory ceiling

- **7 GB model-memory ceiling.**
- Exceeding the memory limit or crashing OOM can result in **disqualification**.
- Peak RSS during any evaluated run must stay below the ceiling — including any co-loaded models (e.g. embedder + LLM + Whisper).

## 5. Scoring weights

- **50%** Accuracy
- **30%** Throughput
- **20%** Efficiency
- **Thermal penalty** where applicable

Priority order that follows from the weights (from PRODUCT.md §13):

1. Agricultural/model accuracy
2. Farm-specific reasoning quality
3. Throughput
4. Memory efficiency
5. Thermal stability
6. African contextual depth
7. UI polish

A beautiful dashboard cannot compensate for a weak local model.

## 6. Runtime and format

- Model format: **GGUF**.
- Inference engine: **llama.cpp**.
- Architecture may treat the inference engine as a swappable component where practical, but the submission implementation must support the required runtime.

## 7. Submission requirements

- Open-source GitHub repo that leverages the approved ADTC 2026 Report Template.
- A comprehensive project report including:
  - Problem definition and context
  - Identified constraints (power, data, compute, connectivity)
  - Documentation of design alternatives and final decisions
  - Tools used and why they were chosen
  - Performance tests and benchmarks
  - Screenshots or short videos showing your build in action
- A short video (max 2 minutes) explaining the solution and development journey.
- Updated repo, documentation and video if selected for semi-final or final round.

## 8. Truthfulness rule

Never fabricate:

- Metrics
- Benchmark scores
- User numbers
- Accuracy
- Adoption
- Deployment scale

All reported numbers must be reproducible from `evaluation/` on the target hardware and recorded in `BENCHMARKS.md`.

## 9. African-language bonus

The competition offers additional score/panel bonus for meaningful African-language functionality. Candidate languages: Hausa, Yoruba, Igbo. FarmTwin's approach (from PRODUCT.md §26) is that a bonus attempt must involve **actual agricultural interaction** in the language — not superficial translation of UI labels. Model accuracy remains more important; do not sacrifice it to chase this bonus.

## 10. 7-day build plan (frozen)

### Day 1 — Foundations and risk retirement

Freeze this document. Set up the Ubuntu 22.04 x86-64 target (or matching VM). Build llama.cpp at a pinned commit. Download two candidate GGUFs (Qwen2.5-3B-Instruct Q4_K_M, Llama-3.2-3B-Instruct Q4_K_M). Verify `llama-server` loads each, measure baseline peak RSS. Scaffold FastAPI + SQLite schema + `sqlite-vec` + Vite/React skeleton.

**Milestone:** `curl` to `llama-server` returns a maize answer locally; the FastAPI app runs and serves the empty React shell.

### Day 2 — Knowledge corpus and RAG pipeline

Curate 60–120 chunks focused on the demo scenario space. Write the ingestion CLI. Choose the embedder based on Day 1 memory headroom. Load the vector store. Manually verify retrieval quality on ~15 sample queries; iterate corpus until decent.

**Milestone:** `scripts/ingest.py` runs clean; a retrieval smoke test returns relevant chunks for the two official test prompts.

### Day 3 — Farm state, deterministic engines, backend end-to-end

Implement the SQLAlchemy models. Write `crop_calendar.py` (maize hardcoded), `risk_rules.py` (6–10 rules for the demo scenario), `context_assembler.py`. Wire the `POST /api/ask` endpoint non-streaming.

**Milestone:** from `curl`, create a farm → log an observation → ask a question → receive a grounded, cited response with a parseable JSON tail.

### Day 4 — Frontend MVP + Landing

Build the landing page as the first task of the day (lowest-risk, most-shippable — natural warm-up). Then proceed with setup, dashboard, Ask panel as originally planned.

**Milestone:** end-to-end via UI, non-streaming; landing → setup → dashboard flows.

### Day 5 — Streaming, citations, polish, and STT plumbing

- Morning: SSE + citations + source drawer + polish.
- Afternoon: build whisper.cpp on the target, download `ggml-base-q5_1.bin`, wire `POST /api/transcribe`, add the mic button + language toggle + `MediaRecorder` on the frontend. Verify a single English clip goes voice → transcript → LLM answer end-to-end.

**Milestone:** full demo flow works with both text and voice input in English.

### Day 5.5 — STT evaluation and gate decision (morning of Day 6)

Record the 15-clip test set. Measure WER for EN and Pidgin. Measure combined peak RSS with both models loaded during a 5-query burst. Decide: ship bilingual, ship EN-only, or (worst case) cut STT and revert Day 5 afternoon changes. Update the demo script to match. **Time-box: 3 hours.**

### Day 6 — Benchmarks and model selection

Unchanged, minus the 3-hour STT gate at the start. LLM/RAG benchmarks and final GGUF selection.

**Milestone:** benchmark table with real numbers; final LLM committed; STT status locked.

### Day 7 — Demo, submission, buffer

Two additions to the demo script:

- Open on the landing page (5 seconds of framing before the CTA).
- In Step 6 of the demo (PRODUCT.md §32), use the mic button to ask the question in English (and, if the Day 5.5 gate passed, ask the follow-up in Pidgin as the visible African-relevance moment). Airplane-mode check now covers STT as well — Whisper must run offline, which it does natively.

## 11. Reproducibility rule

Every benchmark number in the submission must be reproducible by running a documented command from this repo on ADTC-equivalent hardware. If it can't be reproduced, it doesn't go in the report.
