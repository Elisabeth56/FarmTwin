# FarmTwin — Africa Deep Tech Challenge 2026 Submission

**An offline AI digital twin for smallholder farms.**

**Tagline:** Know your farm. Predict what's next. Protect your harvest.

**Submission date:** August 24, 2026
**Target hardware:** ADTC Standard Laptop (8 GB RAM, integrated graphics, CPU inference, Ubuntu 22.04 x86-64)
**Development hardware:** Intel MacBook Pro 2014, 8 GB RAM (deliberately weaker than target — see Limitations)

---

## 1. Problem

Nigerian smallholder farmers face compounding losses from weather shocks, pests, disease, and gaps in agricultural extension coverage. World Bank analysis reports that partial crop losses in Nigeria rose from approximately 6% of plots in 2018/19 to more than 20% of plots in 2023/24, with weather and environmental shocks accounting for nearly two-thirds of those losses. Northeast Nigeria saw partial losses exceeding 40% of plots in the same season. Nigeria's National Agricultural Extension and Research Liaison Services (NAERLS) has reported an extension-agent-to-farmer ratio of approximately 1:6,000 as of 2021 — meaning a farmer with a specific question about their specific field this specific week has almost no realistic path to expert advice in time to act.

The deeper problem is not that agricultural knowledge is missing. Weather forecasts exist. Crop guides exist. Disease identification resources exist. Extension bulletins exist. **The problem is that agricultural knowledge is fragmented and generalized, while farm decisions are local, specific, and time-sensitive.** A farmer needs to know what all of this means for *their* farm, *right now*.

That decision gap is what FarmTwin addresses.

## 2. Product

FarmTwin creates a digital representation of an individual farm — its location, fields, crop, growth stage, observation history, weather context, active risks — and uses a local language model combined with locally-stored agricultural knowledge to produce farm-specific reasoning and actionable recommendations.

The core distinction is not "AI + agriculture." It is: **a generic agricultural assistant knows about maize; FarmTwin knows about *this farmer's* maize.**

Concretely, given a question like *"what should I do this week?"*, FarmTwin:

1. Computes the crop's current growth stage from planting date (deterministic — not the LLM's job)
2. Evaluates rule-based risk flags from recent observations and weather (deterministic)
3. Retrieves 6 relevant chunks from a curated 45-chunk agricultural knowledge corpus using local embeddings and vector search
4. Assembles a structured prompt containing farm facts + retrieved knowledge + question
5. Runs a local 3B-parameter language model that produces a grounded narrative citing specific knowledge chunks and 2-3 prioritized recommendations in a structured schema

Every step of this loop runs on the target laptop. No internet is used for inference, embedding, retrieval, or reasoning.

## 3. Architecture

```
                       BROWSER (React + TypeScript)
                              │
                              ▼
              FastAPI backend (Python 3.11 + SQLite)
                              │
     ┌────────────────────────┼────────────────────────┐
     │                        │                        │
     ▼                        ▼                        ▼
  Deterministic          RAG pipeline           Local LLM
  engines                                       (llama.cpp)
     │                        │                        │
     │                        ▼                        ▼
     │            SentenceTransformer +      llama-server on
     │            sqlite-vec (KNN)           127.0.0.1:8080
     │                                       Qwen2.5-3B Q4_K_M
     │
     ▼
  crop_calendar,
  risk_rules,
  context_assembler

  Voice input (optional):
  MediaRecorder → /api/transcribe → HuggingFace Whisper-small
                                    (Nigerian-accented English)
```
**Component summary:**

- **Frontend:** Vite + React + TypeScript. Three routes (landing, farm setup, dashboard) plus source drawer overlay. Tailwind for styling.
- **Backend:** FastAPI + SQLAlchemy + SQLite. 7 tables, 6 CRUD routers, `/api/ask` streaming endpoint (SSE), `/api/transcribe` for voice input.
- **Deterministic engines:** Growth stage computation from planting date, rule-based risk flag evaluation, prompt assembly. These do the arithmetic, date math, and state tracking so the LLM is not asked to compute what should be computed exactly.
- **RAG pipeline:** 45-chunk agricultural knowledge corpus in `knowledge/corpus/`, embedded once at ingest time using `sentence-transformers/all-MiniLM-L6-v2` (384-dim), stored in SQLite with the `sqlite-vec` extension for KNN retrieval. Query-time retrieval returns top-6 chunks per question.
- **Local LLM:** llama.cpp running Qwen2.5-3B-Instruct at Q4_K_M quantization. Selected through benchmarking (see §5). Streams tokens back via SSE.
- **Voice input (STT):** HuggingFace `rishabbahal/whisper-small-nigerian-accent`, a Whisper-small fine-tune on Nigerian-accented English. Loaded once as a module singleton in the FastAPI process.

**Nothing in this stack calls the internet.** All models, embeddings, and knowledge chunks are local files.

## 4. Design Decisions

### 4.1 Local-first is non-negotiable

The ADTC Laptop LLM Challenge grades systems on their ability to run entirely on the target laptop. This is not a design constraint we chose — it is the premise of the competition. Every architectural decision has been evaluated against: *does this still work with the wifi turned off?* When the answer is no, we redesigned.

Notably: sentence-transformers for embeddings (not OpenAI embeddings), sqlite-vec for vector search (not Pinecone or Weaviate), llama.cpp for inference (not any hosted LLM API), whisper.cpp / HuggingFace Whisper locally (not any speech API).

### 4.2 Deterministic engines separate from the LLM

The LLM does not compute growth stages. It does not do date arithmetic. It does not decide whether a rule fires. Those are deterministic operations handled by `crop_calendar.py` and `risk_rules.py`. The LLM's job is *reasoning over and explaining* the results of those computations, plus retrieved knowledge, plus the user's question.

This matters because small models are unreliable at arithmetic and state tracking. Delegating those to deterministic code frees the LLM to do what it is actually good at: articulating context, distinguishing facts from predictions, and producing structured recommendations.

### 4.3 Corpus curation over corpus size

The knowledge corpus is 45 chunks (12 markdown files, ~450 total pages of source material distilled). Every chunk is attributed to NAERLS, IITA, CIMMYT, or FAO at the organizational level. Chunks are heavily concentrated in the demo scenario space: maize vegetative stage, fungal disease pressure driven by humidity and rainfall, Kaduna agroecology. Rice, cassava, and yam receive small chunks for defensive breadth.

We explicitly chose density over breadth. A retrieval query on the demo scenario returns tightly relevant chunks with strong distance gaps between the top result and the rest, which is what makes the citation quality trustworthy.

### 4.4 Streaming responses via SSE

Local CPU inference on a 3B model takes 2-4 minutes for a full 500-token response. Without streaming, the demo would show 3 minutes of silence before dumping the whole response. With Server-Sent Events, tokens arrive live in the browser — prompt eval still takes ~90 seconds, but generation is visible token-by-token afterward. This is what makes the demo watchable.

### 4.5 Farm-specific narrative + structured JSON

Every response contains two things: a short narrative that connects farm facts to retrieved knowledge (with inline `[K1]` citation chips), and a fenced JSON block containing 2-3 recommendations in a WHAT/WHY/WHEN_URGENCY/RISK_IF_IGNORED/PRIORITY schema. The narrative is what the farmer reads; the structured block is what powers the recommendation cards. Both are parsed at response time.

## 5. Model Selection

Two candidates benchmarked on August 22, 2026, on the development hardware (Intel Mac 2014, 8 GB RAM, matching the ADTC target's resource envelope):

- **Qwen2.5-3B-Instruct Q4_K_M** (1.9 GB on disk)
- **Llama-3.2-3B-Instruct Q4_K_M** (1.9 GB on disk)

A third candidate (Gemma-2-2B) was planned but cut from selection given a single-day compressed benchmarking schedule.

### Test methodology

10 gold prompts including both official ADTC test prompts (Product Knowledge §34) plus 8 farm-scenario variants (vegetative-stage risk assessment, dry-period query, pest observation response, off-domain redirect, stage transition prediction, etc.). Each prompt was run against a farm fixture with specific state — planting date, observations, weather. Same prompts to both models with identical assembly and retrieval.

Manual rubric grading on 5 dimensions (0-5 each):
1. Farm-context grounding — did the response use specific fixture facts?
2. Retrieval grounding — do cited chunks actually support the response's claims?
3. Agronomic factuality — anything wrong versus the corpus?
4. Actionability — are recommendations specific enough to act on?
5. Structure conformance — valid JSON, complete WHAT/WHY/WHEN/RISK, no template echo?

Scoring composite weights (compressed from the ADTC 50/30/20 to reflect the smaller test set): Accuracy 60%, Throughput 25%, Efficiency 15%.

### Results

| Metric | Qwen2.5-3B | Llama-3.2-3B |
|---|---|---|
| Accuracy score | **87.6 / 100** | 82.8 / 100 |
| — Farm-context grounding | 4.80 | 5.00 |
| — Retrieval grounding | **4.20** | 2.60 |
| — Agronomic factuality | 4.90 | 4.30 |
| — Actionability | 4.00 | 4.00 |
| — Structure conformance | 4.00 | 4.80 |
| Prompt eval | **19.0 tok/s** | 18.1 tok/s |
| Generation | **5.4 tok/s** | 3.8 tok/s |
| Wall clock (10 prompts) | **24.1 min** | 29.6 min |
| Peak RSS | **3.06 GB** | 3.53 GB |
| Completion rate | 10/10 | 10/10 |
| **Composite** | **83.5** | 72.9 |

### Decision: Qwen2.5-3B-Instruct Q4_K_M

The determining factor was retrieval grounding. Llama-3.2 produced narratives that read more fluently and had cleaner JSON structure, but it cited chunks that did not actually support its claims — a 1.6-point gap on this dimension. For a system whose entire value proposition rests on *grounded* reasoning, a model that fabricates plausible-looking citations is worse than a model that writes rougher prose but cites correctly.

Qwen was also faster in generation (42% higher throughput) and used 15% less memory. Both fit comfortably under the 7 GB ceiling.

## 6. Benchmarks

All numbers below are measured on the Intel Mac 2014 development machine (8 GB RAM, 4-core Intel CPU, macOS). Numbers are **lower-bound proxy** for the ADTC Ubuntu target; a modern Linux target on comparable hardware should produce equal or better numbers.

### Runtime (Qwen2.5-3B-Instruct Q4_K_M, production configuration)

- **Cold model load:** ~10 seconds
- **Prompt eval:** 17–20 tok/s (varies by prompt size)
- **Generation:** 5.2–5.7 tok/s
- **Full `/api/ask` wall clock:** 2:30–3:00 for typical farm question (~1700 prompt tokens, 250–400 generated)
- **Peak RSS during 3-query burst:** 3.06 GB (44% of 7 GB ceiling)
- **llama.cpp built CPU-only:** `-DGGML_METAL=OFF -DGGML_ACCELERATE=OFF` (matching the target environment; Metal or Accelerate would produce faster numbers but would not reflect the ADTC scenario)

### RAG retrieval

Retrieval on the 45-chunk corpus using `all-MiniLM-L6-v2` embeddings + `sqlite-vec` KNN returns top-6 chunks in well under 100 ms per query. For the demo scenario query *"maize fungal disease risk vegetative stage humidity rainfall Kaduna"*, the top result is chunk `humidity_and_rainfall_as_drivers_of_fungal_disease` (CIMMYT, distance 0.63), with clear distance separation from the next results.

### STT evaluation

15 audio clips (8 English, 7 Nigerian Pidgin, all recorded by a native Pidgin speaker) evaluated against two models:

| | English WER | Pidgin WER |
|---|---|---|
| whisper.cpp base (60 MB multilingual) | 32.8% | 56.1% |
| HuggingFace `rishabbahal/whisper-small-nigerian-accent` (967 MB) | **17.9%** | 58.7% |

The Nigerian-English fine-tune halved English WER but did not meaningfully improve Pidgin. See Limitations §9.

## 7. Offline Operation

FarmTwin was designed offline-first from the frozen v1.0 architecture. Confirmed by:

- **No cloud API calls anywhere in the codebase.** Grep the repo for `openai`, `anthropic`, `cohere`, `pinecone`, `weaviate`, or `googleapis` — you will find zero calls.
- **All model files are local.** `llama-server` reads from `~/farmtwin-models/qwen2.5-3b-instruct-q4_k_m.gguf`. The HuggingFace Whisper model is downloaded once at first use and cached locally; after that no network is required. The sentence-transformers embedder is downloaded at ingestion time and cached.
- **All embeddings are computed locally** during a one-shot ingestion (`scripts/ingest.py`). Query-time embedding for retrieval uses the same local model.
- **The knowledge corpus is text files in the repo.** No hosted knowledge base.
- **The demo includes an airplane-mode segment** where the machine's wifi is turned off before a query is submitted, proving the system continues to operate.

## 8. African Relevance

FarmTwin is aimed at Nigerian smallholder maize farming with Kaduna as the specific demo context. Concrete manifestations:

- **Corpus curated for Nigerian maize.** 42 of 45 chunks focus on maize. Source organizations are Nigerian (NAERLS) and Africa-focused (IITA, CIMMYT for Sub-Saharan Africa). Regional metadata on each chunk allows retrieval filtering.
- **Demo scenario uses SAMMAZ 15** — a Nigerian-developed variety from the Ahmadu Bello University breeding program, familiar to Kaduna farmers.
- **Kaduna agroecology is a first-class corpus topic** — Northern Guinea Savannah, rainy-season timing, sandy loam soil characteristics.
- **Speech-to-text targets Nigerian speech patterns.** We evaluated dedicated Nigerian ASR (see §9 Limitations for the honest assessment of the Nigerian ASR open-source ecosystem as of August 2026) and ship a Whisper-small model fine-tuned specifically on Nigerian-accented English.
- **Hardware target matches African smallholder reality.** The competition's 8 GB Ubuntu laptop specification reflects the class of hardware realistically available. FarmTwin was developed on hardware weaker than the target — a 2014 MacBook Pro with the same 8 GB constraint — as a deliberate stress test.

## 9. Limitations

Honest accounting of what does not work or is imperfect.

### 9.1 Nigerian Pidgin STT is not shipped

Amendment #1 to our frozen architecture accepted bilingual STT (English + Nigerian Pidgin) subject to a Day 5.5 evaluation gate: Pidgin WER must be ≤ 40% on native-speaker recordings for Pidgin to ship. Two models were evaluated:

- **whisper.cpp base multilingual:** 56.1% Pidgin WER
- **rishabbahal/whisper-small-nigerian-accent:** 58.7% Pidgin WER

Both failed the gate. We investigated NCAIR1's `NigerianAccentedEnglish` model (a Nigerian government / Awarri initiative) but found it is a gated HuggingFace repository requiring manual access approval that could not be obtained within the sprint. We also identified Orinode, a Nigerian voice AI company that publishes purpose-built Pidgin ASR with ~9.8% WER per their published benchmarks, but their Q3 2026 rollout timing and open-availability status made integration infeasible for this submission.

**Consequence:** FarmTwin ships with English-only STT, rebranded in the UI as "Voice input (Nigerian English)." The Nigerian-English fine-tune we ship does provide a real quality improvement over base Whisper (17.9% WER vs 32.8%) for English-speaking Nigerian users. Pidgin support is documented as future work in §10.

**This is a real gap in the open-source African ASR ecosystem, not a project-specific failure.**

### 9.2 Small evaluation set

The Day 6 benchmark used 10 gold prompts. Original planning was 30-40 prompts with LLM-as-judge scoring for the non-gold subset. Given the single-day compressed benchmarking schedule and the ~5 minutes per prompt of manual grading, this was cut. The 10 selected prompts do include both official ADTC test prompts plus deliberate coverage of failure modes (off-domain redirect, stage transition, etc.), but a larger test set would produce lower-variance numbers.

### 9.3 Development machine constraints affected schedule

Development took place on an Intel MacBook Pro 2014 (8 GB RAM, 4 cores). During Day 3 we discovered that running the Claude desktop app concurrently with `llama-server` caused CPU-time contention that reduced inference throughput by an order of magnitude. This forced disciplined process management throughout development — kill `llama-server` when editing in VS Code, run browser-based Claude only, etc. Some benchmark runs required repeat measurement to obtain clean numbers. All final benchmark measurements were captured on a clean-boot machine state.

This is documented as ADR-009 in `DECISIONS.md`. It is also an intentional part of the story: we developed and tested on hardware materially weaker than the ADTC target, which increases confidence that the numbers in §6 are a lower bound.

### 9.4 Corpus attribution is at organization level

Every corpus chunk is attributed to NAERLS, IITA, CIMMYT, or FAO. The specific bulletin URLs on each chunk point to the organization's homepage rather than the exact document. This is because the corpus was synthesized from published guidance across each organization's materials rather than transcribed from a single bulletin. Content was cross-checked against multiple independent sources for factual accuracy, but chunk-level provenance is at the organizational rather than document level. This is disclosed on every chunk's `source_note` metadata field.

### 9.5 No image analysis

Vision-based disease diagnosis was considered and explicitly frozen out of scope (§11 of the frozen architecture). It remains valuable and is listed in Future Work.

### 9.6 No live weather integration

Weather snapshots are manually entered by the user. Automated weather ingestion from an API was frozen out of scope to maintain the offline-first guarantee for the core intelligence loop. A future version could allow optional online weather sync while preserving fully-offline core reasoning.

## 10. Future Work

- **Nigerian Pidgin ASR** via Orinode integration (once open availability is confirmed) or a custom fine-tune of Whisper on the AfriSpeech Pidgin subset
- **Vision-based crop disease diagnosis** using a small local image model
- **Optional online weather sync** with cached fallback for offline operation
- **Hausa, Yoruba, and Igbo language support** for both input and output
- **Multi-crop reasoning within one farm** (currently one active crop per field)
- **Yield estimation** using historical observations plus reference agronomic data
- **Push alerts** for time-sensitive risks (currently reactive to user queries)
- **Farmer-to-farmer knowledge sharing** — pseudonymized observation exchange across nearby farms

## 11. Reproducibility

The complete FarmTwin repository is publicly available. To reproduce the demo:

**Requirements:**
- Ubuntu 22.04 x86-64 (or macOS Intel/ARM) with 8+ GB RAM
- Python 3.11 (specifically — see ADR-005)
- Node.js 20+
- CMake, ffmpeg, git-lfs

**Setup:**
```bash
git clone <repo-url> farmtwin
cd farmtwin
./scripts/setup.sh    # (built during Day 7)
```

The setup script downloads the Qwen GGUF (1.9 GB) and the HuggingFace Whisper-small model (~1 GB), builds llama.cpp from a pinned commit, sets up the Python venv, installs npm dependencies, and ingests the corpus.

**Run:**
```bash
./scripts/run.sh
```

Starts llama-server, the FastAPI backend, and the Vite frontend. Open `http://127.0.0.1:5173` in a browser.

**Full detail** on hardware requirements, expected memory footprint, offline verification, and troubleshooting is in `README.md`.

---

*FarmTwin was built by Elisabeth Nnamani as a submission for the Africa Deep Tech Challenge 2026 — Laptop LLM Challenge.*