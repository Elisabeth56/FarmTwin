"""/api/ask and /api/ask/stream. Both run the same prepare step and the same answer handling;
the stream variant sends tokens as they arrive."""

import asyncio
import json
import logging
import time

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.ai import llm
from app.config import get_settings
from app.db.session import get_db
from app.features.ask import answer
from app.features.ask.context import AskContext, prepare
from app.features.ask.schemas import AskIn, AskOut, Recommendation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ask", tags=["ask"])


@router.post("", response_model=AskOut)
def ask(body: AskIn, db: Session = Depends(get_db)):
    started = time.time()
    ctx = prepare(db, body.farm_id, body.question)
    model = get_settings().llm_model
    if ctx.early_answer:
        answer.log_request(ctx, model, "early", {})
        return _out(ctx.early_answer, [], [], [], model, started, {})

    completion = llm.generate(ctx.messages)
    narrative, cards, outcome = _finish(ctx, completion.content)
    cited = answer.cited_chunks(completion.content, ctx.chunks)
    ids = answer.save(db, ctx, cards, cited, model) if cards else []
    answer.log_request(ctx, model, outcome, completion.timings)
    return _out(narrative, cards, cited, ids, model, started, completion.timings)


@router.post("/stream")
async def ask_stream(body: AskIn, db: Session = Depends(get_db)):
    """Server-sent events: ready (all retrieved chunks), token*, then recommendation_ready or error."""
    started = time.time()
    ctx = prepare(db, body.farm_id, body.question)
    model = get_settings().llm_model

    async def events():
        if ctx.early_answer:
            answer.log_request(ctx, model, "early", {})
            yield _sse({"type": "ready", "cited_chunks": []})
            yield _sse(
                {
                    "type": "recommendation_ready",
                    **_out(ctx.early_answer, [], [], [], model, started, {}).model_dump(),
                }
            )
            return

        yield _sse(
            {"type": "ready", "cited_chunks": [answer.chunk_meta(i, c) for i, c in enumerate(ctx.chunks, 1)]}
        )
        parts: list[str] = []
        timings: dict = {}
        async for event in llm.stream(ctx.messages):
            if event["type"] == "token":
                parts.append(event["content"])
                yield _sse(event)
            elif event["type"] == "error":
                answer.log_request(ctx, model, f"error:{event['code']}", {})
                yield _sse(event)
                return
            else:
                timings = event["timings"]

        content = "".join(parts)
        # the repair call is blocking HTTP; keep it off the event loop
        narrative, cards, outcome = await asyncio.to_thread(_finish, ctx, content)
        cited = answer.cited_chunks(content, ctx.chunks)
        try:
            ids = answer.save(db, ctx, cards, cited, model) if cards else []
        except Exception:
            logger.exception("saving recommendations failed")
            db.rollback()
            yield _sse(
                {
                    "type": "error",
                    "code": "save_failed",
                    "message": "The answer couldn't be saved. Try asking again.",
                }
            )
            return
        answer.log_request(ctx, model, outcome, timings)
        yield _sse(
            {
                "type": "recommendation_ready",
                **_out(narrative, cards, cited, ids, model, started, timings).model_dump(),
            }
        )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _finish(ctx: AskContext, content: str) -> tuple[str, list[Recommendation], str]:
    """Narrative and cards, with one repair attempt; outcome is cards, repaired or no_cards."""
    narrative, cards, error = answer.split(content)
    if cards is not None:
        return narrative, cards, "cards"
    logger.warning("recommendations block invalid: %s", error)
    cards = answer.repair(ctx.messages, content, error or "", ctx.prompt_version)
    return narrative, cards or [], "repaired" if cards else "no_cards"


def _out(narrative, cards, cited, ids, model, started, timings) -> AskOut:
    return AskOut(
        narrative=narrative,
        recommendations=[c.model_dump() for c in cards],
        cited_chunks=cited,
        model_name=model,
        timing_ms={
            "prompt_ms": int(timings.get("prompt_ms", 0)),
            "generation_ms": int(timings.get("predicted_ms", 0)),
            "total_ms": int((time.time() - started) * 1000),
        },
        saved_recommendation_ids=ids,
    )


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, default=str)}\n\n"
