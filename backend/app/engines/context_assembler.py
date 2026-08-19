"""Prompt builder for FarmTwin using the Qwen chat template.

Emits <|im_start|>system / user / assistant blocks the way Qwen2.5-Instruct
expects. Includes one inline few-shot example so the model reliably returns
2-3 recommendations (Day 2 shape test only got 1). Truncates retrieved
chunks from the end if the assembled prompt would exceed ~10 000 chars.
"""

from __future__ import annotations

from typing import Any

from app.engines.risk_rules import format_risk_summary


MAX_PROMPT_CHARS = 10_000

SYSTEM_CONTENT = """You are FarmTwin, an offline agricultural advisor for smallholder farmers in West Africa.

Rules:
- Ground every claim in the provided farm state, the rule-based risk flags, or the retrieved agricultural knowledge chunks.
- When you rely on a knowledge chunk, cite it inline using its ID like [K1] or [K3].
- Clearly distinguish farm facts (observed), risk flags (rule-based inference), and recommendations (your advice).
- Do not invent chemical names, dosages, product brands, or prices that are not in the retrieved knowledge.
- Keep the narrative concise: 3-6 sentences.
- Then output a fenced JSON block with 2-3 recommendations using EXACTLY this schema:

```json
{
  "recommendations": [
    {"what": "...", "why": "...", "when_urgency": "immediate|this_week|monitor", "risk_if_ignored": "...", "priority": "high|medium|low"}
  ]
}
```

Example of a well-formed response (illustrative only — use YOUR farm's data):

Heavy rainfall over the past 48 hours combined with sustained humidity puts this vegetative maize crop at elevated risk of foliar fungal disease [K1]. Extension guidance for the region recommends immediate scouting for early lesions and improving field drainage [K2]. If lesions are already visible, a protective fungicide application is advised within the next few days [K1].

```json
{
  "recommendations": [
    {"what": "Scout every row today for leaf lesions or wilting", "why": "Early detection lets you contain a fungal outbreak before it spreads across the field", "when_urgency": "immediate", "risk_if_ignored": "A single missed hot-spot can seed a field-wide outbreak within a week", "priority": "high"},
    {"what": "Clear standing water and improve drainage between rows", "why": "Waterlogged soil under vegetative maize compounds fungal pressure and stresses roots", "when_urgency": "this_week", "risk_if_ignored": "Prolonged waterlogging weakens plants and creates persistent disease conditions", "priority": "high"},
    {"what": "Prepare a protective fungicide application for the next dry window", "why": "Extension guidance recommends protective spraying under these humidity + rainfall conditions", "when_urgency": "this_week", "risk_if_ignored": "Without protection, an outbreak can cost a large share of the yield", "priority": "medium"}
  ]
}
```

Always return the narrative first, then the fenced JSON block. Do not repeat the schema or the example. Return 2 or 3 recommendations."""


def _farm_facts_yaml(facts: dict) -> str:
    """Render a shallow farm-facts dict as compact YAML-ish text."""
    lines: list[str] = []
    for k, v in facts.items():
        if isinstance(v, list):
            if not v:
                lines.append(f"{k}: []")
                continue
            lines.append(f"{k}:")
            for item in v:
                if isinstance(item, dict):
                    parts = ", ".join(f"{ik}: {iv}" for ik, iv in item.items())
                    lines.append(f"  - {{{parts}}}")
                else:
                    lines.append(f"  - {item}")
        elif isinstance(v, dict):
            lines.append(f"{k}:")
            for ik, iv in v.items():
                lines.append(f"  {ik}: {iv}")
        else:
            lines.append(f"{k}: {v}")
    return "\n".join(lines)


def _render_knowledge(chunks: list[dict]) -> str:
    if not chunks:
        return "(No knowledge chunks retrieved. Answer from farm state and risk flags only, and note the missing knowledge.)"
    parts: list[str] = []
    for i, ch in enumerate(chunks, 1):
        org = ch.get("source_org") or "?"
        title = ch.get("chunk_title") or ch.get("source_title") or "(untitled)"
        body = (ch.get("content") or "").strip()
        parts.append(f"[K{i}] ({org}) {title}\n{body}")
    return "\n\n".join(parts)


def assemble_prompt(
    farm_facts: dict,
    risk_flags: list,
    chunks: list[dict],
    user_question: str,
) -> str:
    """Assemble the full Qwen chat-template prompt string.

    Truncates the tail of `chunks` if the total would exceed MAX_PROMPT_CHARS.
    """
    working_chunks = list(chunks or [])

    def build(chks: list[dict]) -> str:
        user_content = (
            "# Farm state\n"
            f"{_farm_facts_yaml(farm_facts)}\n\n"
            "# Rule-based risk flags\n"
            f"{format_risk_summary(risk_flags)}\n\n"
            "# Retrieved agricultural knowledge\n"
            f"{_render_knowledge(chks)}\n\n"
            "# Question\n"
            f"{user_question}\n\n"
            "Respond with the narrative followed by the fenced JSON block "
            "containing 2 or 3 recommendations, as specified in the system instructions."
        )
        return (
            f"<|im_start|>system\n{SYSTEM_CONTENT}<|im_end|>\n"
            f"<|im_start|>user\n{user_content}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

    prompt = build(working_chunks)
    while len(prompt) > MAX_PROMPT_CHARS and working_chunks:
        working_chunks.pop()  # drop least-relevant (last) chunk
        prompt = build(working_chunks)
    return prompt
