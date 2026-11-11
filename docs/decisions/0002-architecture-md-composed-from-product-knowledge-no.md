# 0002 — 2026-08-16 — ARCHITECTURE.md composed from Product Knowledge, not a separate Day 1 architecture doc

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
