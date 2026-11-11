# FarmTwin

**Know your farm. Predict what's next. Protect your harvest.**

FarmTwin is an offline, on-device agricultural assistant for Nigerian smallholder maize farmers and extension officers. It combines a persistent farm digital twin (fields, crops, observations, weather) with a local 3B-parameter LLM grounded in a curated corpus of Nigerian agricultural guidance (NAERLS, IITA, CIMMYT, FAO). Every recommendation is farm-specific, cited to source chunks, and structured — and the whole system runs with the wifi turned off. It is built for the [Africa Deep Tech Challenge 2026 — Laptop LLM Challenge](https://africadeeptechchallenge.com/), on the ADTC 8 GB Ubuntu reference laptop.

---

## Demo

**Demo video: https://youtu.be/j7z2c7UC6_I?si=ppMDkmQKY6wa8GFK

The two-minute demo walks through: landing page → farm setup (Adamu's Farm, Kaduna, SAMMAZ 15 maize, vegetative stage) → dashboard with computed growth stage and days-since-planting → log heavy rainfall + high humidity → a rule-based fungal-risk card fires → open the Ask panel → *"What should I do this week?"* → response streams with `[K1] [K3]` citation chips and a structured WHAT/WHY/WHEN/RISK recommendation card → wifi toggled off → follow-up question runs identically.

---

## Quick start

FarmTwin runs as three local processes: `llama-server` (LLM), FastAPI (backend), and Vite (frontend). Setup is a one-time script; each run needs three terminal tabs.

**Prerequisites** (see [Hardware requirements](#hardware-requirements) for details):
- Python 3.11 (specifically — see [docs/decisions](docs/decisions) ADR-005)
- Node.js 20+
- CMake, ffmpeg, git-lfs
- ~5 GB free disk (Qwen GGUF + Whisper-small + Python/Node deps)

**One-time setup** — assumes `./scripts/setup.sh` has been run. It clones and builds llama.cpp at the pinned commit, downloads the Qwen2.5-3B-Instruct Q4_K_M GGUF (~1.9 GB) and the `rishabbahal/whisper-small-nigerian-accent` model (~1 GB) into `~/farmtwin-models/`, creates the Python 3.11 venv, installs backend + frontend dependencies, and ingests the 45-chunk agricultural corpus into `apps/api/farmtwin.db`.

```bash
./scripts/setup.sh
```

**Run — three tabs:**

Tab 1 — llama-server (LLM):
```bash
~/dev/tools/llama.cpp/build/bin/llama-server \
  -m ~/farmtwin-models/qwen2.5-3b-instruct-q4_k_m.gguf \
  --ctx-size 4096 --threads 4 --load-mode mlock \
  --host 127.0.0.1 --port 8080
```

Tab 2 — FastAPI backend:
```bash
cd backend && source .venv/bin/activate && uvicorn app.main:app --port 8000
```

Tab 3 — Vite frontend:
```bash
cd frontend && npm run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173) in a browser. First inference takes ~90 seconds of prompt eval on a cold cache; generation streams at ~5.4 tok/s thereafter.

---

## Architecture

- **Frontend:** Vite + React 19 + TypeScript + Tailwind. Three routes (landing, farm setup, dashboard) plus a source-drawer overlay.
- **Backend:** Python 3.11 + FastAPI + SQLAlchemy over SQLite. 7 tables, CRUD routers for farms/fields/crops/observations/weather, `POST /api/ask` streaming via Server-Sent Events, `POST /api/transcribe` for voice input.
- **Deterministic engines:** `crop_calendar.py` (growth stage from planting date), `risk_rules.py` (rule-based risk-flag evaluation), `context_assembler.py` (prompt assembly). The LLM is never asked to do arithmetic, date math, or state tracking.
- **RAG:** 45-chunk agricultural corpus in `knowledge/corpus/`, embedded with `sentence-transformers/all-MiniLM-L6-v2` (384-dim), stored in SQLite with the `sqlite-vec` extension for KNN retrieval. Top-6 chunks per query.
- **LLM:** `llama-server` from llama.cpp serving Qwen2.5-3B-Instruct at Q4_K_M quantization (~1.9 GB on disk, ~3.06 GB peak RSS). Selected by benchmark over Llama-3.2-3B — see [benchmarks](docs/v1/benchmarks.md) and [report](docs/v1/report.md) §5.
- **STT:** HuggingFace `rishabbahal/whisper-small-nigerian-accent` — a Whisper-small fine-tune on Nigerian-accented English. Loaded once as a module singleton in the FastAPI process.

Nothing in this stack calls the internet at runtime. Full architectural detail — including the frozen v1.0 architecture and Amendment #1 — is in [v1 architecture](docs/v1/architecture.md).

---

## Repository structure

```
FarmTwin/
├── apps/
│   ├── web/              Vite + React + TypeScript app UI
│   └── api/              FastAPI + SQLAlchemy + sqlite-vec
│       ├── app/          api, db, engines, llm, rag, stt
│       └── scripts/      ingest and smoke tests
├── knowledge/corpus/     curated agricultural corpus (NAERLS, IITA, CIMMYT, FAO)
├── evals/
│   ├── v1/               v1 gold prompts, benchmark runner and results
│   └── stt/              speech clips, WER scripts and write-ups
├── docs/
│   ├── architecture.md   v2 architecture
│   ├── decisions/        ADR-001 to ADR-026, one file each
│   └── v1/               frozen v1 documents (product, hackathon, architecture, benchmarks, report)
└── AGENTS.md             engineering rules for coding agents
```

---

## Key documents

- [report](docs/v1/report.md) — The full technical writeup submitted to ADTC. Design decisions, model selection with numbers, offline verification, honest limitations.
- [v1 architecture](docs/v1/architecture.md) — Frozen v1.0 architecture (MVP, user journey, LLM role, RAG, data model, screens, backend components, benchmark strategy) plus Amendment #1 (landing page + STT).
- [docs/decisions](docs/decisions) — Chronological ADR log covering every deviation from the frozen documents.
- [benchmarks](docs/v1/benchmarks.md) — Day 1 baselines, Day 2 shape test, Day 6 model-selection benchmark. Only measured numbers.
- [hackathon](docs/v1/hackathon.md) — The ADTC 2026 rules (domain, hardware, 7 GB memory ceiling, scoring, submission requirements, truthfulness rule).
- [product](docs/v1/product.md) — The frozen product knowledge (tagline, positioning, demo scenario, official ADTC test prompts).
- [AGENTS.md](AGENTS.md) — Engineering rules that governed every coding session during the sprint.
- [evaluation/stt_results/day5_5_wer.md](evaluation/stt_results/day5_5_wer.md), [evaluation/stt_results/day5_5_wer_hf.md](evaluation/stt_results/day5_5_wer_hf.md) — STT evaluation, both candidate models.

---

## ADTC 2026 submission

FarmTwin is a submission to the **Africa Deep Tech Challenge 2026 — Laptop LLM Challenge** in the **Agriculture** domain.

- **Submission repo:** *[Link to be added — separate repo with the ADTC report template]*
- **DevPost project page:** *[Link to be added after publication]*

The submission repo (`farmtwin-adtc-submission`) contains the report against the approved ADTC template, the model card, `metadata.json`, and the run instructions. This public repo is the full working system — code, corpus, evaluation harness, and reproducible benchmarks.

---

## Hardware requirements

FarmTwin targets the ADTC Standard Laptop profile:

| Component | Requirement |
| --- | --- |
| RAM | **8 GB minimum** (7 GB model-memory ceiling per ADTC rules) |
| CPU | x86-64, 4 cores or better; integrated graphics is fine — no discrete GPU needed |
| Disk | ~5 GB free (Qwen GGUF ~1.9 GB + Whisper-small ~1 GB + Node/Python deps) |
| OS | Ubuntu 22.04 LTS (reference target) or macOS Intel/ARM |
| Python | 3.11 (specifically — see ADR-005) |
| Node | 20+ |
| Other | CMake, ffmpeg, git-lfs |

Peak RSS during a 3-query burst on the reference model is **3.06 GB** — 44% of the 7 GB ceiling. Development happened on a 2014 Intel MacBook Pro with 8 GB RAM, deliberately weaker than the ADTC target, so the reported numbers are a lower bound.

---

## Acknowledgements

- **NAERLS, IITA, CIMMYT, and FAO** — source organizations for the agricultural knowledge corpus. Every chunk in `knowledge/corpus/` is attributed to one of these at the organizational level; content was cross-checked against multiple published bulletins for factual accuracy (see [report](docs/v1/report.md) §9.4 for the honest note on chunk-level provenance).
- **`rishabbahal/whisper-small-nigerian-accent`** on HuggingFace — the Whisper-small fine-tune on Nigerian-accented English that ships as the STT model.
- **llama.cpp**, **sqlite-vec**, **sentence-transformers**, and the wider open-source local-LLM ecosystem that makes offline-first ML on a $400 laptop possible at all.
- **Anthropic Claude** — used for pair programming during the 7-day sprint. Every architectural decision, every design tradeoff, and every line committed was reviewed and owned by the author; Claude accelerated implementation but did not choose the shape of the system.

---

## License

MIT — see [LICENSE](LICENSE).

---

*Built by Elisabeth Nnamani for the Africa Deep Tech Challenge 2026 — Laptop LLM Challenge.*
