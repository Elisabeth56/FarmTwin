# ADR-018: Hybrid retrieval with a relevance cutoff

- Status: Accepted
- Date: 2026-11-11

## Context
v1 retrieval was vector-only and always returned 6 chunks. With no cutoff, a question the corpus cannot answer still gets 6 "sources", and a 3B model cites them. The corpus grows from 12 maize files to six crops (ADR-019), which adds more near-miss chunks.

## Options
- **Vector only.** Current; misses exact terms (variety names, pest names) and has no "nothing relevant" signal.
- **Hybrid: vector + FTS5 keyword, merged with reciprocal rank fusion, plus a cutoff.**
- **Hybrid + cross-encoder reranker.** Better ranking, but adds a model and noticeable latency on a 2014 CPU.

## Decision
Hybrid search with reciprocal rank fusion, filtered by crop in SQL before ranking. If the best vector match falls below a threshold tuned on the eval set, the ask endpoint skips generation and returns the "not in my sources" response. Keep the top 4–6 chunks.

## Consequences
- The threshold is a tuned number, so it lives in settings and the eval reports its effect.
- A reranker is added only if the eval shows retrieval misses that hybrid search does not fix.
