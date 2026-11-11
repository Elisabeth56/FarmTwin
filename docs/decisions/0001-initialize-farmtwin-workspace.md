# 0001 — 2026-08-16 — Initialize FarmTwin workspace

**Status:** accepted
**Context:** Day 1 of the ADTC 2026 build. The frozen Product Knowledge (§§1–41), the ADTC hackathon rules, and the Day 1–3 plan exist as text but aren't yet committed as repo docs.
**Decision:** Create the FarmTwin repo skeleton at `/Users/macbookpro/Documents/FarmTwin` with the seven directories listed in `ARCHITECTURE.md §4` and the six top-level markdown files: `PRODUCT.md`, `HACKATHON.md`, `ARCHITECTURE.md`, `AGENTS.md`, `DECISIONS.md`, `BENCHMARKS.md`.

- `PRODUCT.md` — copied verbatim from the approved Product Knowledge.
- `HACKATHON.md` — ADTC constraints (domain, hardware, memory ceiling, scoring, runtime, submission, truthfulness) plus the frozen 7-day plan.
- `ARCHITECTURE.md` — technical shape derived from PRODUCT.md §§6, 7, 11, 15, 16, 17, 18, 19, 20, 21 and the Day 1–3 plan.
- `AGENTS.md` — engineering rules for any coding agent.
- `DECISIONS.md` — this log.
- `BENCHMARKS.md` — empty template. No numbers yet.

**Alternatives considered:**

- Build the repo in the ephemeral cloud sandbox and export later. Rejected — the sandbox is discarded on session end, and the canonical repo needs to be on disk with git.
- Also inline a `README.md`. Deferred — no user-facing content warranted on Day 1; will be added when Day 1 tasks (llama.cpp build, first `curl` to `llama-server`) start producing setup instructions worth writing down.

**Consequences:**

- All future work anchors to this layout. Adding a top-level directory requires a new decision entry (per AGENTS.md §8).
- The four frozen documents can't be edited casually — every change must be paired with a decision here.

**Links:** created via initial workspace setup on 2026-08-16.

---
