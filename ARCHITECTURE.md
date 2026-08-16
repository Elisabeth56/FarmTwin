# FarmTwin — Architecture Decision Document (v1.0 Frozen + Amendment #1)

# Part I — Frozen v1.0 Architecture

Scope frozen against the Product Knowledge doc and ADTC 2026 constraints. No new features are entertained past this point. Any deviation must be justified against the decision rule in §40 of the Product Knowledge.

---

## 1. Exact MVP

FarmTwin v1.0 lets one farmer create one farm with one field and one active crop, log observations against that field, view a computed farm state, and ask a local LLM a farm-specific question that returns a grounded, cited, structured recommendation — fully offline.

Nothing else is in scope. Concretely, the MVP proves this loop end-to-end:

1. Create farm → add field → add crop with planting date
2. Log at least one observation (rainfall, pest, disease, or note) and one weather snapshot
3. See deterministically-computed growth stage, days since planting, and rule-derived risk flags
4. Ask a natural-language question in the Ask panel
5. Backend assembles farm facts + retrieved knowledge chunks + question, sends to llama.cpp
6. Response streams back with inline citations and a structured recommendation card (WHAT/WHY/WHEN/RISK)
7. Everything above works with the machine airplane-moded

That is the entire MVP. Multi-farm, auth, image analysis, live weather, language switching, yield ML, mobile — all out.

---

## 2. Exact User Journey

There is one canonical journey. It matches the demo scenario in §10.

1. **First launch** → Landing view with a single "Create your farm" call to action.
2. **Farm setup** (single screen, one form): farm name, region (Kaduna preset for demo), area in hectares, one field with soil type, one crop with variety and planting date. Submit.
3. **Land on dashboard**: farm summary header, current crop card showing computed growth stage and days since planting, empty risk panel, empty observations feed, crop timeline strip, "Ask FarmTwin" panel docked on the right.
4. **Log an observation**: user opens quick-log modal, selects type (rainfall / humidity / pest / disease / note), enters value and date, submits. Dashboard rerenders. If a rule fires, a risk card appears with reason and severity.
5. **Ask a question**: user types into the Ask panel. Response streams. Citation chips appear inline; clicking a chip opens a drawer with the source chunk. A structured recommendation card is emitted below the narrative.
6. **Follow-up**: user asks a related question; context is refreshed from current farm state each turn (no long chat memory).
7. **Offline validation**: user toggles wifi off (or judge does), repeats step 5. Same behavior.

No other paths exist in the UI. There is no settings screen, no profile, no logout, no history browser beyond the on-screen observation feed and last-N-recommendations panel.

---

## 3. Exact Local LLM Role

The LLM is a **reasoning and articulation engine only**. It is never used for arithmetic, date math, unit conversion, or state tracking.

Responsibilities of the LLM:
- Read the assembled prompt (farm facts block + retrieved knowledge block + user question)
- Produce a short natural-language narrative that connects farm-specific facts to relevant retrieved knowledge
- Cite the knowledge chunks it relied on by ID (e.g. [K3])
- Distinguish farm facts from retrieved knowledge from predictions from recommendations
- Emit a trailing structured JSON block with 1–3 recommendations in the WHAT/WHY/WHEN/RISK schema

Non-responsibilities:
- Computing growth stage → deterministic (`crop_calendar.py`)
- Computing days since planting or expected harvest window → deterministic
- Deciding whether a rule-based risk fires → deterministic (`risk_rules.py`)
- Persisting anything → backend
- Choosing which chunks to retrieve → retriever
- Chit-chat, roleplay, non-agricultural questions → politely redirect

Runtime: served by `llama-server` from llama.cpp as a local HTTP process on 127.0.0.1, GGUF model at Q4_K_M or Q5_K_M quantization. Model family shortlist to benchmark (final choice deferred to Day 6, per §14 of Product Knowledge): Qwen2.5-3B-Instruct, Llama-3.2-3B-Instruct, Phi-3.5-mini-instruct (~3.8B), Gemma-2-2B-it. Context window capped at 4096 tokens for the MVP to protect the memory ceiling.

---

## 4. Exact RAG Role

RAG serves two purposes and only two purposes:

1. **Ground agricultural claims** in a curated, offline corpus so the small model does not have to rely on parametric knowledge.
2. **Surface farm-record snippets** (recent observations, latest weather, current crop state) as retrievable context alongside general knowledge.

Corpus composition (frozen for MVP, ~60–120 chunks total):
- Maize lifecycle and stage-specific management
- Maize diseases with an emphasis on humidity/rainfall-triggered fungal pressure (rust, blight, downy mildew)
- Maize pest pressure at vegetative stage
- Soil management basics for sandy loam / Northern Nigeria conditions
- Kaduna and broader Northern Nigeria agroecological notes
- General agronomic guidance for smallholder maize
- Small amounts of rice/cassava/yam material as stretch, only if Day 2 finishes ahead

Deep breadth is explicitly rejected in favor of demo-scenario density.

Ingestion pipeline (one-shot script, run at build time):
- Sources stored as `/knowledge/*.md` files with YAML frontmatter (source, region, crop, topics)
- Chunking: ~500-token windows with ~100-token overlap
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2` (~90 MB) as the default; `bge-small-en-v1.5` (~130 MB) as fallback if retrieval quality is poor
- Vector store: SQLite with the `sqlite-vec` extension (single file, ships with the app, zero external dependencies)
- Optional keyword index: SQLite FTS5 over the same chunks, for hybrid retrieval

Retrieval at query time:
- Query composed by a small deterministic function combining crop, growth stage, top-risk keywords, region, and the user's question
- Top-6 chunks by cosine similarity from `sqlite-vec`
- Optional post-filter by region/crop tags in the frontmatter
- Farm records (recent observations, latest weather, current crop state) are pulled directly from SQLite by ID — they are not embedded — and inserted as a separate labeled block in the prompt

Each chunk retains `source_id`, `source_title`, `region`, `crop`, `topic` — surfaced as citation metadata in the UI.

---

## 5. Exact Farm Digital-Twin Data Model

Persisted in SQLite. Minimal, MVP-shaped. No foreign-key surprises.

- `farms(id, name, region, latitude, longitude, area_hectares, created_at)`
- `fields(id, farm_id, name, area_hectares, soil_type, soil_ph_estimate, notes)`
- `crops(id, field_id, crop_type, variety, planting_date, status, created_at)` — one active crop per field for MVP
- `observations(id, field_id, obs_type, value_numeric, value_text, unit, observed_at, created_at)` — obs_type ∈ {rainfall, humidity, temperature, pest, disease, note}
- `weather_snapshots(id, farm_id, snapshot_date, rainfall_mm, temp_min_c, temp_max_c, humidity_pct, notes)` — manually entered in MVP, no API
- `recommendations(id, farm_id, field_id, what, why, when_urgency, risk_if_ignored, priority, cited_chunk_ids, model_name, created_at)`
- `document_chunks(id, source_id, source_title, region, crop, topics, content, embedding)` — via `sqlite-vec`

Derived-but-not-stored (computed on read by deterministic engines):
- Current growth stage per crop
- Days since planting
- Expected harvest window
- Active rule-based risk flags with reason and severity

The "living" property of the twin comes from these derivations plus the observations feed, not from a heavyweight simulation.

---

## 6. Exact Frontend Screens

Three screens. That is the entire frontend surface.

**Screen 1 — Farm setup (`/setup`).** One form, three logical groups (Farm, Field, Crop). Submits three sequential POSTs. On success, redirects to the dashboard.

**Screen 2 — Farm dashboard (`/farm/:id`).** Single-page layout:
- Header: farm name, region, area
- Left column: current crop card (stage, days since planting, expected harvest window from the deterministic engine), crop timeline strip, latest weather snapshot, observations feed with a "Log observation" button
- Center: risk panel (rule-derived cards) and recommendations panel (last N LLM-generated recommendations)
- Right column: docked "Ask FarmTwin" panel (chat surface)

**Screen 3 — Source drawer (overlay, not a route).** Opens from any citation chip. Shows the full chunk text, source title, region, and topic tags. Read-only.

Landing/onboarding text is a small block on `/setup` when no farms exist — not a separate route. No settings, no profile, no history page. The observation feed and recommendations panel on the dashboard cover "history" for the MVP.

*(Note: Amendment #1 revises this to add a proper landing page route. See Part II.)*

Stack: Vite + React + TypeScript, Tailwind, a small component set (shadcn/ui components only where they earn their keep). Design tone: modern, muted greens and warm neutrals, generous whitespace, no dashboard chart-junk.

---

## 7. Exact Backend Components

Python 3.11, FastAPI, running as a single process. Serves both the API and the built static frontend from the same origin.

- **API layer** (`app/api/`): `farms`, `fields`, `crops`, `observations`, `weather`, `ask`, `sources`. `ask` streams via SSE.
- **Persistence** (`app/db/`): SQLAlchemy models over SQLite, plus a thin wrapper around `sqlite-vec` for vector search.
- **Deterministic engines** (`app/engines/`):
  - `crop_calendar.py` — growth stage, day counts, harvest windows (hardcoded lifecycles for maize; stubs for rice/cassava/yam if time)
  - `risk_rules.py` — 6–10 rules covering the demo scenario space (heavy rainfall + vegetative maize → fungal risk, prolonged high humidity → disease pressure, extended dry spell + vegetative → moisture stress, etc.)
  - `context_assembler.py` — builds the final prompt from farm state + retrieved chunks + question, applies the output schema instruction
- **Retrieval** (`app/rag/`): query builder, embedder wrapper, vector search, optional FTS hybrid, chunk formatter with `[K1]…[Kn]` IDs
- **LLM client** (`app/llm/`): thin HTTP client to `llama-server`, streams tokens, parses the trailing JSON block
- **Ingestion CLI** (`scripts/ingest.py`): one-shot corpus builder — not part of the runtime
- **llama.cpp**: `llama-server` binary from a pinned commit, launched as a supervised subprocess on backend startup with the chosen GGUF, `-c 4096`, mmap enabled

No message queue, no Redis, no background workers, no auth, no Docker required at runtime (though a Dockerfile ships for reproducibility).

---

## 8. Exact Model Inference Flow

Per user question:

1. Frontend `POST /api/ask` with `{farm_id, question}` (SSE connection opens).
2. Backend loads farm state: farm, fields, active crops, last 30 days of observations, latest weather snapshot.
3. Deterministic pass computes: current growth stage per crop, days since planting, expected harvest window, active rule-based risk flags.
4. Query builder composes a compact retrieval query from `(crop, growth_stage, top_risk_keywords, region, question_topic)`.
5. Retriever embeds the query, runs top-6 vector search in `sqlite-vec` (optionally rescored with FTS), applies region/crop filters.
6. Context assembler produces the final prompt with these labeled blocks:
   - **System instruction**: role, grounding rule ("answer using only the provided farm facts and knowledge chunks; cite chunk IDs; distinguish facts, retrieved knowledge, predictions, recommendations"), output schema
   - **Farm facts**: compact YAML block of the deterministically-computed state
   - **Knowledge**: numbered chunks `[K1]…[K6]` with title + content
   - **User question**
   - **Response schema hint**: brief narrative, then a fenced JSON block with `recommendations[]` and `confidence`
7. Backend streams the request to `llama-server` and pipes tokens to the SSE channel.
8. As tokens arrive, frontend renders narrative live. When streaming ends, backend parses the trailing JSON, persists to `recommendations`, and pushes a final `recommendation_ready` SSE event with the parsed structure and chunk IDs.
9. Frontend renders recommendation cards; citation chips in the narrative are cross-linked to the source drawer.

Per-turn context is rebuilt fresh from current farm state. No multi-turn chat memory in the MVP — this is a decision to protect prompt size and reduce failure modes.

---

## 9. Exact Benchmark Strategy

Three metric families matching the ADTC weighting (50/30/20).

**Test set.** 30–40 curated farm-specific prompts including both official test prompts (§34 of Product Knowledge). Each item ships with: a farm-state fixture (seed data inserted before the query), the question, and a rubric answer key listing must-hit facts, must-cite source topics, and expected recommendation shape.

**Accuracy (50%).** Rubric with five dimensions scored 0–5 each: farm-context grounding, retrieval grounding (are cited chunks actually relevant), agronomic factuality vs. corpus, actionability of the recommendation, structure conformance (valid JSON, WHAT/WHY/WHEN/RISK present). Ten gold items graded manually; remainder graded via LLM-as-judge using a stronger model at benchmark time only (this is offline dev-time evaluation, not runtime — the runtime remains 100% local). Report mean per dimension and aggregate.

**Throughput (30%).** Per candidate `(model, quant, n_ctx)`:
- Cold-load time to first `/health` OK
- Time-to-first-token on a standardized 1.2k-token prompt
- Prompt-eval tokens/s and generation tokens/s
- End-to-end wall-clock for the full 30-item throughput subset

**Efficiency (20%).** Per candidate:
- Peak RSS via `/usr/bin/time -v` for the whole backend process during a 5-query burst
- Sustained RSS sampled every 500 ms via `psutil` during the same burst
- Delta with mmap on vs. off
- Delta at `n_ctx` = 2048 vs. 4096 vs. 8192
- Confirm ceiling: total resident set must stay under 7 GB with headroom for the OS

**Test hardware.** Primary run on the ADTC target-spec laptop (8 GB, integrated graphics, Ubuntu 22.04 x86-64, CPU inference). If a target unit is unavailable, use a Docker container capped at 8 GB RAM / 8 vCPUs on x86-64 Ubuntu 22.04 as a proxy and clearly label it as such.

**Candidates.** Qwen2.5-3B-Instruct, Llama-3.2-3B-Instruct, Phi-3.5-mini-instruct (~3.8B), Gemma-2-2B-it — all at Q4_K_M and, where memory permits, Q5_K_M.

**Reporting.** A single table per candidate covering all three metric families. **No numbers reported until measured.** If a run fails or a candidate exceeds the memory ceiling, that is reported as a result, not hidden.

---

## 10. Exact Demo Scenario

Single coherent story, ~5 minutes, one farm, one field, one crop, one weather event, one question, one offline check. Aligned to §32 of the Product Knowledge.

1. Open FarmTwin on the target laptop. Landing screen. Click "Create your farm."
2. Fill in: **"Adamu's Farm"**, Kaduna, 2.5 ha. Field: "Main Field", sandy loam. Crop: **Maize**, SAMMAZ variety, planting date set so the demo lands the crop in the **vegetative stage**.
3. Land on the dashboard. Point at: current stage badge, days since planting, expected harvest window — all computed by `crop_calendar.py`, not the LLM.
4. Open quick-log twice. Add **heavy rainfall (~65 mm over 48 h)** and **elevated humidity (~85%)**.
5. Dashboard rerenders. A rule-based risk card appears: elevated fungal disease pressure for maize in the vegetative stage under sustained high humidity.
6. Open the Ask panel. Type: **"What should I do this week?"**
7. Response streams. Citation chips `[K1] [K3] [K4]` appear inline. Recommendation card materializes with 2–3 prioritized actions in WHAT/WHY/WHEN/RISK form.
8. Click a citation chip → source drawer opens → close it.
9. **Toggle wifi off visibly.** Ask a follow-up: **"How urgent is the fungal risk given the growth stage?"** Same behavior.
10. Briefly show the benchmarks page or a printed summary: model name, tokens/s, peak memory, accuracy rubric aggregate.

Narration explicitly contrasts a generic answer ("maize can get fungal disease") with FarmTwin's answer ("your maize, planted June 12, currently vegetative, with the rainfall and humidity you logged this week, is at elevated fungal risk — here is what to do in the next 24–72 hours, citing [K1] and [K3]"). That contrast is the single most important beat in the demo.

---

## 11. Features We Explicitly Will NOT Build

Frozen out for v1.0. No exceptions without unfreezing this document.

- Image / vision disease diagnosis
- Multi-farm, multi-user, authentication, roles
- Live weather API integration (weather is manually entered)
- Yield-prediction ML model
- African-language response mode (deferred — the "meaningful" bar in §26 of the Product Knowledge cannot be met in 7 days without pulling from higher-priority work)
- Fine-tuning or LoRA of the base model (base + strong prompting + RAG only)
- Advanced RAG: cross-encoder reranking, HyDE, query decomposition, agentic retrieval
- Multi-turn chat memory beyond the current turn
- Mobile / native / PWA install flow (browser only)
- Notifications, cron, background alerting
- PDF export, sharing, report generation
- Boundary drawing on a map (centroid coordinates only)
- Historical analytics dashboards, charts beyond the crop timeline strip
- Onboarding tutorials, tooltips, help center
- Settings, preferences, theme switching
- Feedback loop / thumbs-up-down that changes model behavior
- Cloud sync, remote backup, telemetry
- Marketplace, finance, insurance, IoT — anything from §36 of the Product Knowledge

If any of the above appears in the submission, the scope freeze has been violated.

*(Note: Amendment #1 modifies this list — landing page added, English-only STT ruled in, other exclusions strengthened. See Part II.)*

---

## 12. Biggest Technical Risks

Ordered by likely blast radius on the submission.

1. **Model is not good enough at 3B–3.8B for the reasoning bar.** Mitigation: benchmark on Day 5 (not Day 6) if possible, keep Phi-3.5-mini as a heavier fallback within the 7 GB ceiling, invest heavily in prompt structure and few-shot examples in `context_assembler.py`.
2. **RAG retrieves irrelevant chunks.** Mitigation: tightly curate the corpus around the demo scenario; use region/crop tag filtering; keep chunks small; hybrid vector + FTS if pure vector under-recalls.
3. **Peak memory blows the 7 GB ceiling.** Mitigation: measure on Day 1 with the real backend loaded, not just `llama-server` in isolation; prefer Q4_K_M; cap `n_ctx` at 4096; do embeddings at ingestion time only and unload the ST model at runtime; forbid running the browser dev tools during the demo.
4. **Prompt bloat pushes effective context past the model's useful range.** Mitigation: prune farm state to fields relevant to the question type; summarize observations older than 30 days into a one-liner; hard-cap retrieved chunks at 6.
5. **LLM ignores retrieved context and hallucinates.** Mitigation: strict system prompt with a cite-or-abstain instruction; 1–2 few-shot examples showing correct citation behavior; structured output schema; a lightweight backend post-check that flags responses with zero citations.
6. **llama.cpp integration surprises on the exact Ubuntu 22.04 target.** Mitigation: pin the llama.cpp commit; build and smoke-test on the Ubuntu 22.04 environment on Day 1 before writing any other code that depends on it.
7. **Streaming (SSE) plumbing eats a day.** Mitigation: ship non-streaming on Day 3 as the working default; add streaming Day 5 only after the rest is green; keep it fallback-able.
8. **Judges miss the farm-specific angle** and read the demo as a generic chatbot. Mitigation: the Day 10 narration script that explicitly contrasts generic vs. farm-context answers; the UI keeps farm facts and citations visible during response rendering.
9. **Benchmark results are weak** on the throughput axis. Mitigation: run benchmarks realistically and lead the submission narrative with accuracy and efficiency (where a small model has a real story) rather than hiding the numbers.
10. **Single-point-of-failure on any teammate or subsystem.** Mitigation: pair on the risky path (llama.cpp + FastAPI streaming) on Day 1; keep the repo runnable end-to-end from Day 3 onward so any commit that breaks main is caught same-day.

---

## 13. Seven-Day Implementation Order

Assumes a 1–3 person team with you (full-stack) leading. If solo, drop styling polish on Day 4 and the FTS hybrid on Day 2.

**Day 1 — Foundations and risk retirement.**
Freeze this document. Set up the Ubuntu 22.04 x86-64 target (or matching VM). Build llama.cpp at a pinned commit. Download two candidate GGUFs (Qwen2.5-3B-Instruct Q4_K_M, Llama-3.2-3B-Instruct Q4_K_M). Verify `llama-server` loads each, measure baseline peak RSS. Scaffold FastAPI + SQLite schema + `sqlite-vec` + Vite/React skeleton. **Milestone:** `curl` to `llama-server` returns a maize answer locally; the FastAPI app runs and serves the empty React shell.

**Day 2 — Knowledge corpus and RAG pipeline.**
Curate 60–120 chunks focused on the demo scenario space. Write the ingestion CLI. Choose the embedder based on Day 1 memory headroom. Load the vector store. Manually verify retrieval quality on ~15 sample queries; iterate corpus until decent. **Milestone:** `scripts/ingest.py` runs clean; a retrieval smoke test returns relevant chunks for the two official test prompts.

**Day 3 — Farm state, deterministic engines, backend end-to-end.**
Implement the SQLAlchemy models. Write `crop_calendar.py` (maize hardcoded), `risk_rules.py` (6–10 rules for the demo scenario), `context_assembler.py`. Wire the `POST /api/ask` endpoint non-streaming. **Milestone:** from `curl`, create a farm → log an observation → ask a question → receive a grounded, cited response with a parseable JSON tail.

**Day 4 — Frontend MVP.**
Build the farm setup screen, dashboard (farm summary, crop card, timeline strip, risk panel, observations feed, quick-log modal), and the Ask panel shell. Style with the frozen design tone. Connect all read/write endpoints except streaming. **Milestone:** end-to-end via the UI, non-streaming.

**Day 5 — Streaming, citations, polish.**
Convert `/api/ask` to SSE, wire the frontend to render tokens live and finalize with a `recommendation_ready` event. Build the source drawer and citation chips. Add loading/empty/error states. Swap in the second candidate GGUF via config to confirm nothing is hardcoded to one model. **Milestone:** full demo flow works UI-to-LLM with streaming, citations, and observations flowing through.

**Day 6 — Benchmarks and model selection.**
Run the benchmark harness across candidates. Grade the 10 gold items manually; LLM-judge the rest. Measure throughput and efficiency on the target machine. Pick the final model. Update the prompt template based on observed failure modes. Freeze the GGUF file into the release. **Milestone:** benchmark table with real numbers; final model committed.

**Day 7 — Demo, submission, buffer.**
Rehearse the 5-minute demo script twice end-to-end, including the airplane-mode moment. Record a backup video. Bug-bash the top 5 issues surfaced during rehearsal. Write the submission document from the Product Knowledge §33 outline, using only real numbers. Package the repo with a reproducible README (pinned commit, model download URLs, `make run`, expected memory footprint, offline instructions). Keep 2–3 hours of buffer for whatever breaks. **Milestone:** submitted.

---

*This concludes the frozen v1.0 architecture. Any change from here on requires an explicit unfreeze and a written trade-off against the 7-day timeline.*

---
---

# Part II — Amendments

## Amendment #1: Landing Page + English/Nigerian Pidgin Speech-to-Text

**Date:** 2026-08-16
**Status:** Accepted (STT with Day 5.5 evaluation gate)

Two additions to the frozen v1.0 architecture, evaluated against the decision rule (§40 of Product Knowledge) and the 7-day timeline.

### Verdict

**Landing page — ACCEPTED.** Low cost, high demo value, already implied by §28 of Product Knowledge. Formalized as its own route rather than a block on `/setup`.

**Speech-to-text (English + Nigerian Pidgin) — ACCEPTED WITH CONSTRAINTS.** Real African-relevance win (§25, §26 of Product Knowledge) that materially improves the demo. Introduces a new model, new memory pressure, and new failure modes on a 7-day clock. Accepted only with the constraints below. If any constraint slips, STT is cut on Day 5.5 and text-only ships. Non-negotiable — the LLM + RAG loop is the graded system; STT cannot compromise it.

### Changes to MVP (amends §1 of Part I)

Add: a landing page at `/`, and a microphone button in the Ask panel that transcribes English or Nigerian Pidgin speech into the same text field the user would otherwise type into.

STT is an **input modality only**. It does not change the LLM flow, the RAG flow, the prompt structure, the data model, the recommendation schema, or the response path. Transcribed text goes into the existing `POST /api/ask` endpoint unchanged.

### Changes to User Journey (amends §2 of Part I)

New Step 0: **Landing page (`/`).** Hero, one-line value prop, one CTA ("Create your farm"), a short "How it works" strip (3 steps), a footer noting offline operation and the ADTC context. Click CTA → `/setup`.

Step 5 gains an alternative: user taps the mic button in the Ask panel, speaks in English or Pidgin, sees the transcript appear in the input field, can edit it, then submits. Everything downstream is identical.

### Changes to Frontend Screens (amends §6 of Part I)

Now **four** screens (three routes + one overlay):

- **Screen 1 — Landing (`/`).** New. Static, no data fetching, no auth. Hero + 3-step explainer + CTA. Copy generated from the Product Knowledge per §30.
- **Screen 2 — Farm setup (`/setup`).** Unchanged.
- **Screen 3 — Farm dashboard (`/farm/:id`).** Ask panel gains a mic button and a small language-hint toggle (`EN / Pidgin`) sitting next to it. Toggle defaults to `EN`. During recording, a waveform or pulsing indicator; on stop, transcript populates the input field for user review before submit.
- **Screen 4 — Source drawer.** Unchanged.

### Changes to Backend Components (amends §7 of Part I)

Add one component:

- **STT service** (`app/stt/`): thin wrapper around `whisper.cpp` running as a supervised subprocess on backend startup, exposing `POST /api/transcribe` which accepts an audio blob + language hint and returns `{text, language_detected, duration_ms}`.

Everything else in §7 of Part I stands.

### Changes to Local Model Layer (amends §3 and §14 of Part I / Product Knowledge)

Now two local models loaded at runtime:

- **LLM**: unchanged — llama.cpp + GGUF (Qwen2.5-3B or equivalent, Q4_K_M)
- **STT**: whisper.cpp + GGML/GGUF Whisper model

**Whisper model choice** — must fit inside the 7 GB total ceiling alongside the LLM. Candidates, in preference order:

1. `ggml-base.en-q5_1.bin` (~60 MB) — English only, fastest, smallest. Use if Pidgin support is weak everywhere.
2. `ggml-base-q5_1.bin` (~60 MB) — multilingual base. First choice for the multilingual case.
3. `ggml-small-q5_1.bin` (~200 MB) — multilingual small. Fallback if base cannot handle Pidgin acceptably.

Larger Whisper variants (medium, large) are rejected — they will not fit alongside the LLM.

**Honest note on Nigerian Pidgin.** Whisper's Pidgin support is not first-class. Nigerian Pidgin is not one of Whisper's officially listed languages. In practice Whisper often transcribes it via the English path with reasonable results for Pidgin that is lexically close to English, and worse results for deeply idiomatic Pidgin. **We will not claim Pidgin ASR accuracy we have not measured.** The Day 5.5 evaluation below is a gate, not a formality. If Pidgin performance is unusable, the language toggle ships as `EN only` and we describe the Pidgin work as "initial evaluation, deferred" in the submission — which is still an honest, defensible position under §33 of Product Knowledge.

Runtime handling: whisper.cpp will be invoked per request. The Whisper model is loaded once at backend startup and kept resident. Language parameter is passed through: `en` when the toggle is EN; `en` again as the safest default for Pidgin (letting Whisper's English decoder handle Pidgin-adjacent speech) — with a config flag to try `auto` or a specific alternative if evaluation shows it helps.

### Changes to Data Model (amends §5 of Part I)

Zero schema change. Transcripts are ephemeral: they populate the input field, get submitted as text, and are not persisted separately. Audio observations were considered and rejected — out of scope.

### Changes to Model Inference Flow (amends §8 of Part I)

Prepend two optional steps when the mic is used:

- **Step 0a**: Frontend records audio via `MediaRecorder` (WebM/Opus), stops on user tap or silence timeout (default 15 s cap).
- **Step 0b**: Frontend `POST /api/transcribe` with the blob + language hint. Backend converts to 16 kHz mono WAV via `ffmpeg` (already a whisper.cpp dependency in practice), runs whisper.cpp, returns transcript.
- Frontend populates the Ask input with the transcript. User reviews and edits if needed. User submits.

From that point on, steps 1–9 of §8 of Part I are unchanged. STT is strictly upstream of the graded reasoning path.

### Changes to Benchmark Strategy (amends §9 of Part I)

Add a **fourth, separate** evaluation for STT that does not commingle with the ADTC-weighted metrics:

- **Test set**: 15 short audio clips (5–15 s each) — 8 English, 7 Nigerian Pidgin — of the kinds of questions a farmer would actually ask ("what should I do this week", "is my maize at risk from the rain"). Recorded by team members or sourced from openly-licensed corpora where available.
- **Metrics**: Word Error Rate per language, mean transcription latency on the target machine, peak additional RSS with Whisper loaded.
- **Gate**: if Pidgin WER > ~40% on our clips **or** Whisper + LLM combined peak RSS crosses 6.5 GB (leaving headroom under the 7 GB ceiling), Pidgin is disabled and we ship English-only STT.

The main accuracy/throughput/efficiency table in §9 of Part I continues to reflect the LLM+RAG system only. STT numbers are reported separately in the submission.

### Changes to Risks (amends §12 of Part I)

Three new risks:

- **R11 — Whisper + LLM breach the 7 GB ceiling.** Mitigation: measure both loaded together on Day 5.5 before the demo is locked; downgrade Whisper to `base.en-q5_1` (English-only) if needed; last resort, unload Whisper between requests (accept latency cost).
- **R12 — Pidgin ASR quality is unusable.** Mitigation: honest evaluation, ship EN-only if it fails, do not oversell.
- **R13 — Browser microphone permissions or codec issues on the target laptop.** Mitigation: test `MediaRecorder` + `ffmpeg` pipeline on the target OS on Day 5; ship a "type instead" affordance that is always visible next to the mic button.

Additionally, R3 (memory ceiling) is now more likely to bite — it moves up to the #2 slot in priority.

### Changes to Non-Features List (amends §11 of Part I)

Explicitly still out, even given this amendment:

- Voice **output** (TTS) — text response only
- Speaker diarization, wake-word, hands-free mode
- Recording history, audio playback, audio in the observations feed
- Live streaming transcription — we transcribe on tap-stop, not continuously
- African languages other than English and Nigerian Pidgin (no Hausa/Yoruba/Igbo in v1.0)
- LLM response generation in Pidgin — the model responds in English; only input is bilingual. Adding Pidgin output would require prompt engineering and evaluation we do not have time for, and the small models we are considering are unlikely to produce quality Pidgin. This is the honest call.

### Revised Seven-Day Order (amends §13 of Part I)

Days 1–3 unchanged from the frozen plan. STT slots into Day 5 and gets a dedicated half-day gate.

**Day 4 — Frontend MVP + Landing.**
Add: build the landing page as the first task of the day. Then proceed with setup, dashboard, Ask panel as originally planned. **Milestone:** end-to-end via UI, non-streaming; landing → setup → dashboard flows.

**Day 5 — Streaming, citations, polish, and STT plumbing.**
Morning: SSE + citations + source drawer + polish (as originally planned).
Afternoon: build whisper.cpp on the target, download `ggml-base-q5_1.bin`, wire `POST /api/transcribe`, add the mic button + language toggle + `MediaRecorder` on the frontend. Verify a single English clip goes voice → transcript → LLM answer end-to-end. **Milestone:** full demo flow works with both text and voice input in English.

**Day 5.5 — STT evaluation and gate decision (morning of Day 6).**
Record the 15-clip test set. Measure WER for EN and Pidgin. Measure combined peak RSS with both models loaded during a 5-query burst. **Decide:** ship bilingual, ship EN-only, or (worst case) cut STT and revert Day 5 afternoon changes. Update the demo script to match. Time-box this to 3 hours.

**Day 6 — Benchmarks and model selection.**
Unchanged, minus the 3-hour STT gate at the start. LLM/RAG benchmarks and final GGUF selection as originally planned. **Milestone:** benchmark table with real numbers; final LLM committed; STT status locked.

**Day 7 — Demo, submission, buffer.**
Unchanged, with two additions to the demo script:
- Open on the landing page (5 seconds of framing before the CTA).
- In Step 6 of the demo (§10 of Part I), use the mic button to ask the question in English (and, if the Day 5.5 gate passed, ask the follow-up in Pidgin as the visible African-relevance moment). Airplane-mode check now covers STT as well — Whisper must run offline, which it does natively.

### Revised Demo Beats (amends §10 of Part I)

The demo now opens and includes voice:

- **Beat 0 (new, 10 s)**: Landing page. Read the hero line. Click "Create your farm."
- Beats 1–5 unchanged.
- **Beat 6 (revised)**: Tap the mic. Speak in English: *"What should I do this week?"* Transcript appears, submit, response streams with citations.
- **Beat 9 (revised)**: Airplane mode on. Tap mic. If Day 5.5 passed, ask the follow-up in Pidgin. If not, ask in English. Same offline behavior.

The narration line becomes: *"FarmTwin runs the model, the knowledge base, and the speech recognizer entirely on this laptop, with no network."* Stronger closing beat than the frozen plan had.

### What This Amendment Deliberately Does NOT Do

- Not adding a settings page for language selection — the toggle lives in the Ask panel where it is used.
- Not persisting audio or transcripts.
- Not adding an "audio observation" feature (record a note about the field). Tempting, out of scope.
- Not localizing the UI into Pidgin — labels stay in English.
- Not touching the LLM prompt to encourage Pidgin output.

---