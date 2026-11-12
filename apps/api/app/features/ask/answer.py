"""Turns the model's text into what the app shows: narrative, validated recommendation cards,
and the chunks it actually cited."""

import json
import logging
import re

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai import llm, prompts
from app.db import models
from app.errors import AppError
from app.features.ask.context import AskContext
from app.features.ask.schemas import Recommendation, RecommendationBlock

logger = logging.getLogger(__name__)

FENCE_RE = re.compile(r"```json\s*(.*?)```", re.DOTALL | re.IGNORECASE)
CITATION_RE = re.compile(r"\[K(\d+)\]")
PRIORITY = {"high": 1, "medium": 2, "low": 3}


def split(content: str) -> tuple[str, list[Recommendation] | None, str | None]:
    """Returns (narrative, cards or None, why the cards failed)."""
    fence = content.find("```")
    narrative = (content[:fence] if fence >= 0 else content).strip()
    blocks = FENCE_RE.findall(content)
    if not blocks:
        return narrative, None, "there was no ```json block"
    try:
        block = RecommendationBlock.model_validate_json(blocks[-1].strip())
    except ValidationError as exc:
        return narrative, None, _short_error(exc)
    return narrative, block.recommendations, None


def repair(messages: list[dict], content: str, error: str, version: str) -> list[Recommendation] | None:
    """One retry asking only for a corrected JSON block. None if that fails too."""
    retry = [
        *messages,
        {"role": "assistant", "content": content},
        {"role": "user", "content": prompts.load(version, "repair").format(error=error)},
    ]
    try:
        fixed = llm.generate(retry, max_tokens=400, temperature=0.0)
    except AppError:
        return None
    _, cards, still_wrong = split(fixed.content)
    if cards is None:
        logger.warning("repair failed: %s", still_wrong)
    return cards


def cited_chunks(content: str, chunks: list[dict]) -> list[dict]:
    """The chunks the narrative cites with [K#], in citation order; unknown IDs are ignored."""
    indices = sorted({int(m) for m in CITATION_RE.findall(content)})
    return [chunk_meta(i, chunks[i - 1]) for i in indices if 1 <= i <= len(chunks)]


def chunk_meta(index: int, chunk: dict) -> dict:
    keys = (
        "chunk_id",
        "source_id",
        "source_org",
        "source_title",
        "chunk_title",
        "content",
        "region",
        "crop",
        "topics",
        "distance",
    )
    return {"citation": f"K{index}", **{k: chunk.get(k) for k in keys}}


def save(
    db: Session, ctx: AskContext, cards: list[Recommendation], cited: list[dict], model: str
) -> list[int]:
    cited_ids = json.dumps([c["chunk_id"] for c in cited]) if cited else None
    rows = [
        models.Recommendation(
            farm_id=ctx.farm.id,
            field_id=ctx.primary_field_id,
            what=card.what,
            why=card.why,
            when_urgency=card.when_urgency,
            risk_if_ignored=card.risk_if_ignored,
            priority=PRIORITY[card.priority],
            cited_chunk_ids=cited_ids,
            model_name=model,
        )
        for card in cards
    ]
    db.add_all(rows)
    db.commit()
    return [r.id for r in rows]


def log_request(ctx: AskContext, model: str, outcome: str, timings: dict) -> None:
    logger.info(
        "ask farm=%s prompt=%s model=%s chunks=%s outcome=%s timings=%s",
        ctx.farm.id,
        ctx.prompt_version,
        model,
        [c["chunk_id"] for c in ctx.chunks],
        outcome,
        timings,
    )


def _short_error(exc: ValidationError) -> str:
    first = exc.errors()[0]
    where = ".".join(str(p) for p in first["loc"]) or "block"
    return f"{where}: {first['msg']}"
