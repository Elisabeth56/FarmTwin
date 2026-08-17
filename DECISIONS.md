# DECISIONS.md — FarmTwin decision log

Chronological, append-only record of decisions that shape FarmTwin. Every deviation from `PRODUCT.md`, `HACKATHON.md`, `ARCHITECTURE.md`, or `AGENTS.md` must land here. Every change to those frozen documents must also land here.

## Entry format

```markdown
## NNNN — YYYY-MM-DD — Short title

**Status:** proposed | accepted | superseded by NNNN | reversed
**Context:** what forced the decision — the situation, constraint, or observation.
**Decision:** what we chose.
**Alternatives considered:** what else we looked at and why we didn't pick it.
**Consequences:** what this makes easier, what it makes harder, what it commits us to.
**Links:** related commits, files, benchmark rows, or prior decisions.
```

Keep entries short. Prefer more entries over long ones. Do not delete or rewrite past entries — supersede them.

---

## 0001 — 2026-08-16 — Initialize FarmTwin workspace

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

## 0002 — 2026-08-16 — ARCHITECTURE.md composed from Product Knowledge, not a separate Day 1 architecture doc

**Status:** accepted
**Context:** The instruction was to "document the final architecture in ARCHITECTURE.md" based on the "approved Day 1 architecture." No separate approved Day 1 architecture document was supplied. The Product Knowledge (§§6, 7, 11, 15, 16, 17, 18, 19, 20, 21) plus the Day 1–3 plan does contain the architectural material.
**Decision:** Compose `ARCHITECTURE.md` from those sections, plus the Day 5 STT plumbing note, and freeze the resulting shape. If a distinct approved architecture document surfaces later, reconcile it against `ARCHITECTURE.md` in a new decision entry.
**Alternatives considered:**

- Leave `ARCHITECTURE.md` as a TODO scaffold. Rejected — Day 1 needs a frozen architecture to build against.
- Ask and wait. Rejected — the source material was sufficient to write a defensible architecture today.

**Consequences:**

- If the referenced approved Day 1 architecture doc says something different, this file gets superseded, not silently overwritten.

**Links:** `ARCHITECTURE.md`.
llama tag b10472
ADR-004: llama.cpp tag bXXXX uses --load-mode mlock instead of --mlock. Older tutorials will show the old flag; ours must use the new one.

## ADR-005: Python interpreter mismatch on host
Date: 2026-08-17
Status: Accepted
Context: `python3` on this Mac resolves to Python 3.14; pydantic-core 
wheels don't build against PyO3 0.22 on 3.14 yet.
Decision: Use `/usr/local/bin/python3.11` explicitly for the venv:
`python3.11 -m venv .venv` (not `python3 -m venv .venv`).
Consequences: setup.sh on Day 7 must detect and use 3.11 specifically. 
Judges' machines may also have this issue.

## ADR-006: FastAPI trailing-slash routing
Date: 2026-08-17
Status: Accepted
Context: FastAPI's default trailing-slash redirect on `POST /api/farms/` 
returns 307 and curl drops the body on redirect.
Decision: Route paths inside prefixed routers use `""` not `"/"`, so 
`POST /api/farms` resolves directly without redirect.
Consequences: All future routers follow this convention.

## ADR-007: Vite dev server binds to IPv4 explicitly
Date: 2026-08-17
Status: Accepted
Context: Vite 9 defaults to IPv6-only loopback, causing 127.0.0.1 to refuse.
Decision: Set `server.host: '127.0.0.1'` in vite.config.ts.
Consequences: setup.sh instructions and README can use either 127.0.0.1 
or localhost consistently.