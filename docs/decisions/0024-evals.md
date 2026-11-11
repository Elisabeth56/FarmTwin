# ADR-024: Eval harness with retrieval metrics and a 40+ case golden set

- Status: Accepted
- Date: 2026-11-11

## Context
v1 had 10 hand-graded prompts, all maize, with no retrieval metric and no unanswerable cases. v2 changes the embedder, retrieval, corpus and possibly the model, and each change needs a number to compare against.

## Decision
- `evals/cases.jsonl` with 40+ cases: all six crops, intercropping, questions the corpus cannot answer, and Pidgin-phrased questions. Each case has a farm fixture, the question, expected key facts, and expected source ids.
- Retrieval: recall@k and MRR against expected source ids, plus how often the cutoff correctly refuses.
- Answers: rule checks for structure and citations; an LLM judge for faithfulness and correctness, using a free-tier API at dev time only. The app itself stays fully offline. A sample is hand-graded to check the judge.
- Ops: time to first token, tokens per second, peak memory on the target laptop.
- One command (`pnpm eval`) prints a table and saves JSON; results are compared with the last saved baseline.
- The STT WER test from ADR-011 moves into `evals/stt/` unchanged.

## Consequences
- Prompt, chunking, embedder or model changes are accepted only with an eval run.
- Every bad answer reported in testing becomes a new case.
