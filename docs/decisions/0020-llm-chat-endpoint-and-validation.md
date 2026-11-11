# ADR-020: llama-server chat endpoint, validated output, re-benchmark

- Status: Accepted
- Date: 2026-11-11

## Context
v1 called `/completion` with a hand-written Qwen chat template and parsed the last fenced JSON block with a regex. Swapping models meant editing the template, and invalid JSON was silently dropped.

## Options
- **Keep `/completion` with a custom template.**
- **`/v1/chat/completions`.** llama-server applies the chat template stored in the GGUF file.

## Decision
Use `/v1/chat/completions` with streaming. Prompts move to versioned files in `ai/prompts/`. The trailing recommendations block is validated with Pydantic; on failure, one repair retry, then the answer is shown without cards and the failure is logged. All provider access sits in one module exposing `generate()` and `stream()`.

Re-run the ADR-012 benchmark against current 3–4B instruct models with the v2 eval set (six crops, Pidgin questions). Qwen2.5-3B-Instruct Q4_K_M stays unless a candidate beats it on accuracy within the memory ceiling.

## Consequences
- A model swap is a config change plus an eval run.
- The benchmark adds a Pidgin-understanding slice, since ADR-025 sends Pidgin transcripts to the LLM.
