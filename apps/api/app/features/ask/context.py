"""Loads everything an answer needs: the farm, each active planting with its stage and risks,
recent readings, retrieved knowledge, and the rendered prompt. Shared by both ask endpoints."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.ai import prompts
from app.db import models
from app.db.lookup import farm_or_404
from app.engines.farm_state import PlantingState, latest_weather, planting_states
from app.rag import retriever

MAX_PROMPT_CHARS = 12_000

NO_PLANTING = "This farm has no active planting yet. Add one with a crop and planting date, then ask again."
# shown instead of an answer when retrieval finds nothing close enough (ADR-018)
NOT_IN_SOURCES = (
    "I couldn't find this in FarmTwin's farming guides, so I won't guess. I can help with your "
    "crops' growth stages, pests, diseases, weather risks, planting and harvest."
)


@dataclass
class AskContext:
    farm: models.Farm
    plantings: list[PlantingState]
    chunks: list[dict]
    messages: list[dict]
    prompt_version: str
    # set when the answer is known without the model
    early_answer: str | None = None
    # answer | no_planting | not_in_sources: lets the app skip sources for a non-answer
    kind: str = "answer"

    @property
    def primary_field_id(self) -> int | None:
        return self.plantings[0].field.id if self.plantings else None


def prepare(db: Session, farm_id: int, question: str, today: date | None = None) -> AskContext:
    today = today or date.today()
    farm = farm_or_404(db, farm_id)
    version = prompts.ASK_VERSION

    weather = latest_weather(db, farm.id)
    states = planting_states(db, farm, weather, today)
    if not states:
        return AskContext(farm, [], [], [], version, early_answer=NO_PLANTING, kind="no_planting")

    crops = sorted({s.planting.crop_type for s in states})
    query = retriever.build_query(
        crop_type=" ".join(crops),
        growth_stage=" ".join(dict.fromkeys(s.stage["stage"] for s in states)),
        region=farm.region or "",
        risk_flags=[r for s in states for r in s.risks],
        user_question=question,
    )
    found = retriever.retrieve(query, crops, top_k=6, db_session=db)
    if found.refused:
        return AskContext(farm, states, [], [], version, early_answer=NOT_IN_SOURCES, kind="not_in_sources")

    messages = render_messages(farm, states, weather, found.chunks, question, today, version)
    return AskContext(farm, states, found.chunks, messages, version)


def render_messages(
    farm: models.Farm,
    states: list[PlantingState],
    weather: dict | None,
    chunks: list[dict],
    question: str,
    today: date,
    version: str,
) -> list[dict]:
    """System + user messages; drops the least relevant chunks if the prompt grows too long."""
    system = prompts.load(version, "system")
    template = prompts.load(version, "user")
    kept = list(chunks)
    while True:
        user = template.format(
            farm=_farm_text(farm, states, weather, today),
            risks=_risks_text(states),
            knowledge=knowledge_text(kept),
            question=question,
        )
        if len(system) + len(user) <= MAX_PROMPT_CHARS or not kept:
            return [{"role": "system", "content": system}, {"role": "user", "content": user}]
        kept.pop()


def knowledge_text(chunks: list[dict]) -> str:
    if not chunks:
        return "(none)"
    return "\n\n".join(
        f"[K{i}] ({c.get('source_org') or '?'}) {c.get('chunk_title') or c.get('source_title')}\n"
        f"{(c.get('content') or '').strip()}"
        for i, c in enumerate(chunks, 1)
    )


def _farm_text(farm: models.Farm, states: list[PlantingState], weather: dict | None, today: date) -> str:
    lines = [
        f"Farm: {farm.name}" + (f", {farm.region}" if farm.region else ""),
        f"Today: {today.isoformat()}",
    ]
    for s in states:
        p, st = s.planting, s.stage
        parts = [f"stage {st['stage']}"]
        if p.planting_date:
            parts.insert(0, f"planted {p.planting_date.isoformat()}, day {st['days_since_planting']}")
        if st["expected_harvest_range"]:
            start, end = st["expected_harvest_range"]
            parts.append(f"harvest expected {start.isoformat()} to {end.isoformat()}")
        lines.append(
            f"- {p.crop_type}{f' ({p.variety})' if p.variety else ''} in field '{s.field.name}'"
            f"{f', {s.field.soil_type} soil' if s.field.soil_type else ''}: {', '.join(parts)}"
        )
    if weather:
        readings = ", ".join(f"{k} {v}" for k, v in weather.items() if k != "snapshot_date" and v is not None)
        lines.append(f"Latest weather ({weather['snapshot_date'].isoformat()}): {readings or 'no readings'}")
    else:
        lines.append("Latest weather: none recorded")
    return "\n".join(lines)


def _risks_text(states: list[PlantingState]) -> str:
    lines: list[str] = []
    for s in states:
        for f in s.risks:
            lines.append(
                f"- {s.planting.crop_type}, field '{s.field.name}' "
                f"[{f.severity.upper()} / {f.time_sensitivity}] {f.name}: {f.reason}"
            )
            lines.extend(f"    - {fact}" for fact in f.supporting_facts)
    return "\n".join(lines) or "No rule-based risks fired."
