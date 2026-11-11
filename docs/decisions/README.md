# Decisions

One file per decision. ADR-001 to ADR-012 come from the v1 hackathon build and are kept unchanged. ADR-013 onward cover the v2 remodel.

## v1 entry format

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
