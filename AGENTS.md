# AGENTS.md — Rules for coding agents working on FarmTwin

Any AI coding agent (Claude Code, other Claude sessions, Copilot, Cursor, etc.) or human contributor must follow these rules. They are enforced by review, not by tooling. When a rule blocks you, log the trade-off in `docs/decisions/` rather than working around it silently.

## 1. Sources of truth

- `docs/v1/product.md` is the frozen product knowledge. Do not paraphrase, rewrite, or "improve" it.
- `docs/v1/hackathon.md` is the frozen ADTC constraint set. Its rules override any local convenience.
- `docs/v1/architecture.md` is the frozen technical shape. Deviations require a `docs/decisions/` entry.
- If any of the three seem wrong, propose an edit in a `docs/decisions/` entry — do not just change them.

## 2. Do not fabricate

- **Never invent benchmark numbers.** No tokens/sec, no peak RSS, no accuracy score enters `docs/v1/benchmarks.md`, the README, the report, the UI, the video, or the pitch unless it came from a real run on the target hardware.
- **Never invent implementation status.** If a feature is scaffolded but not working, say "scaffolded." If it isn't started, say "not started." Do not say "implemented" for stubs.
- **Never invent agricultural claims.** If a claim can't be traced to a chunk in `knowledge/`, either add a real source or drop the claim.
- **Never invent citations.** When the LLM produces a citation, it must reference an actual retrieved chunk ID.

## 3. Offline-first is not optional

- No app code may call a cloud LLM, cloud embedder, or remote vector service. This includes OpenAI, Claude, Gemini, Cohere, Pinecone, Weaviate cloud, and anything similar.
- No outbound HTTP from runtime paths. Package downloads at build time are fine; runtime network calls are not.
- If a package pulls in a telemetry/analytics dependency, disable it or replace the package.
- The airplane-mode test on Day 7 is the source of truth.

## 4. Memory budget is a hard requirement

- Combined peak RSS for anything loaded during evaluation must stay under **7 GB** (docs/v1/hackathon.md §4).
- Before adding a model, embedder, or in-memory index, measure the delta and record it in `docs/v1/benchmarks.md`.
- Prefer streaming and lazy loading. Load whisper.cpp only when transcribing.

## 5. Deterministic-first

- Dates, timelines, thresholds, unit conversions, and simple arithmetic go in Python, not in the prompt (docs/v1/product.md §18).
- The LLM's job is to reason over and explain deterministic results, not to compute them.
- If you catch yourself asking the model to "calculate," rewrite it as code.

## 6. Farm-specific reasoning, always

- Every `/api/ask` call must include the current farm's state in the prompt (docs/v1/product.md §10).
- Generic answers that ignore the farm's crop, stage, or history are bugs.
- Recommendations must include WHAT / WHY / WHEN / RISK (docs/v1/product.md §22).

## 7. Scope discipline

- The MVP is the intelligence loop in docs/v1/product.md §31. Ship that end-to-end before polishing any of it.
- Do not add features that fail the decision rule in docs/v1/product.md §40.
- Explicitly out of scope for the hackathon: marketplace, banking, insurance, drones, IoT, satellite analytics, auth, multi-tenant, cloud sync (docs/v1/product.md §36).
- Disease image analysis (§23) and yield prediction (§24) are de-prioritized behind the core LLM + RAG + farm-state loop.

## 8. Repository layout

The v2 layout is set by ADR-026 (`docs/decisions/0026-website-and-repo-layout.md`). Do not add top-level directories without a decision record.

- `apps/web/` — Vite/React app UI.
- `apps/api/` — FastAPI, SQLAlchemy models, deterministic engines, RAG glue, and its scripts.
- `apps/desktop/` — Tauri shell (added in M5).
- `apps/site/` — Astro + Starlight website (added in M6).
- `packages/twin/` — the 3D farm scene shared by the site and the app (ADR-028).
- `knowledge/` — curated corpus and crop rule files.
- `evals/` — golden sets, benchmark and WER harnesses, saved results.
- `docs/` — architecture, decisions, and the frozen v1 documents in `docs/v1/`.
- GGUF and other model files are gitignored. Do not commit multi-GB binaries.

## 9. Pins and reproducibility

- llama.cpp is built at a **pinned commit** (recorded in `model/README.md` or equivalent when Day 1 executes).
- Python deps go in `apps/api/requirements.txt` or `pyproject.toml` with pinned versions.
- Node deps: use the lockfile. Do not `npm install` without committing the lock change.
- Every benchmark number in `docs/v1/benchmarks.md` must be reproducible from a single documented command.

## 10. Test prompts are the acceptance bar

The two official test prompts in docs/v1/product.md §34 are the acceptance bar for the intelligence loop. If the system can't answer both with:

- correct farm context,
- retrieved and cited knowledge chunks,
- distinguished facts vs. predictions,
- prioritized, actionable recommendations,

then the MVP is not done, regardless of what the UI looks like.

## 11. Working with the ephemeral cloud vs. the Mac folder

- The canonical repo is on the Mac at `/Users/macbookpro/Documents/FarmTwin`.
- Cloud sandbox scratch does not survive session end. Commit important work to the Mac folder before finishing.
- Files edited on the Mac and files staged into the cloud container are separate filesystems — pick one location per file and don't mix.

## 12. Commit messages and decisions

- Keep commit messages short and factual. No marketing.
- If a commit changes any of the four frozen documents (`docs/v1/product.md`, `docs/v1/hackathon.md`, `docs/v1/architecture.md`, `AGENTS.md`), the commit must also add or reference an entry in `docs/decisions/`.

## 13. What "done" means

A task is done when:

1. It works on the target hardware profile (or on a matching VM if the target isn't in hand).
2. It has real numbers in `docs/v1/benchmarks.md` if it's a performance-sensitive component.
3. Its status is truthfully reflected in the current progress report and the README.
4. It respects the memory ceiling and offline-first rule.

Anything short of that is "in progress."
