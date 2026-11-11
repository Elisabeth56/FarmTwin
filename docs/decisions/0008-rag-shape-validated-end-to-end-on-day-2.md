# ADR-008: RAG shape validated end-to-end on Day 2
Date: 2026-08-18
Status: Accepted
Context: Verified that retrieval + prompt assembly + local LLM produces a farm-specific, cited, structured response with valid JSON.
Decision: Freeze the RAG pipeline as-is. Iterate on prompting quality on Day 3.
Consequences: Day 3 can build the /api/ask endpoint knowing the underlying pipeline works.
Known Day 3 improvements: use Qwen chat-template tokens, add few-shot examples, fix JSON parser to grab last fenced block.
