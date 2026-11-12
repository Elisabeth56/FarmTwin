# ADR-012: Final model selection — Qwen2.5-3B-Instruct Q4_K_M
Date: 2026-08-22
Status: Accepted
Context: Day 6 benchmark of 2 candidates on 10 gold prompts. Manual rubric grading.
Decision: Qwen2.5-3B wins composite (83.5 vs Llama-3.2 72.9). Key differentiator:
Llama scored 2.6/5.0 on retrieval grounding vs Qwen's 4.2/5.0 — Llama hallucinated
citations. In a RAG-based system, correct citation is more important than smooth prose.
Consequences: 
- Qwen GGUF is the shipped model for submission
- setup.sh (Day 7) downloads only Qwen from Hugging Face
- REPORT.md documents both candidates with honest numbers
- Llama-3.2 file can stay in ~/farmtwin-models/ for local reference but not required
