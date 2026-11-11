"""Loads everything an answer needs: the farm, each active planting with its stage and risks,
recent readings, retrieved knowledge, and the rendered prompt. Shared by both ask endpoints."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.ai import prompts
from app.db import models
from app.db.lookup import farm_or_404
from app.engines.rules import RiskFlag, evaluate, growth_stage
from app.rag import retriever

OBSERVATION_DAYS = 30
MAX_OBSERVATIONS = 12
MAX_PROMPT_CHARS = 12_000

NO_PLANTING = "This farm has no active planting yet. Add one with a crop and planting date, then ask again."
# shown instead of an answer when retrieval finds nothing close enough (ADR-018)
NOT_IN_SOURCES = (
    "I couldn't find this in FarmTwin's farming guides, so I won't guess. I can help with your "
    "crops' growth stages, pests, diseases, weather risks, planting and harvest."
)


@dataclass
class PlantingState:
    planting: models.Planting
    field: models.Field
    stage: dict[str, Any]
    risks: list[RiskFlag]


@dataclass
class AskContext:
    farm: models.Farm
    plantings: list[PlantingState]
    chunks: list[dict]
    messages: list[dict]
    prompt_version: str
    # set when the answer is known without the model
    early_answer: str | None = None

    @property
    def primary_field_id(self) -> int | None:
        return self.plantings[0].field.id if self.plantings else None


def prepare(db: Session, farm_id: int, question: str, today: date | None = None) -> AskContext:
    today = today or date.today()
    farm = farm_or_404(db, farm_id)
    version = prompts.ASK_VERSION

    # each active planting gets its own stage and risks, from its own field's readings
    weather = _latest_weather(db, farm.id)
    states: list[PlantingState] = []
    for field in farm.fields:
        observations = _recent_observations(db, field.id, today)
        for planting in field.plantings:
            if planting.status != "active":
                continue
            stage = _stage(planting, today)
            risks = evaluate(planting.crop_type, stage["stage"], observations, weather, today)
            states.append(PlantingState(planting, field, stage, risks))
    if not states:
        return AskContext(farm, [], [], [], version, early_answer=NO_PLANTING)

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
        return AskContext(farm, states, [], [], version, early_answer=NOT_IN_SOURCES)

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


def _stage(planting: models.Planting, today: date) -> dict[str, Any]:
    planted = planting.planting_date
    if planted is not None:
        try:
            return growth_stage(planting.crop_type, planted, today)
        except ValueError:
            pass  # crop without a rule file: the answer still works, just without a calendar
    return {
        "stage": "unknown",
        "days_since_planting": (today - planted).days if planted else None,
        "total_cycle_days": 0,
        "expected_harvest_range": None,
        "description": "",
    }


def _recent_observations(db: Session, field_id: int, today: date) -> list[dict]:
    since = datetime.combine(today - timedelta(days=OBSERVATION_DAYS), datetime.min.time())
    rows = (
        db.query(models.Observation)
        .filter(models.Observation.field_id == field_id, models.Observation.observed_at >= since)
        .order_by(models.Observation.observed_at.desc())
        .limit(MAX_OBSERVATIONS)
        .all()
    )
    return [
        {
            "obs_type": o.obs_type,
            "value_numeric": o.value_numeric,
            "value_text": o.value_text,
            "unit": o.unit,
            "observed_at": o.observed_at.date(),
        }
        for o in rows
    ]


def _latest_weather(db: Session, farm_id: int) -> dict | None:
    row = (
        db.query(models.WeatherSnapshot)
        .filter(models.WeatherSnapshot.farm_id == farm_id)
        .order_by(models.WeatherSnapshot.snapshot_date.desc())
        .first()
    )
    if row is None:
        return None
    return {
        "snapshot_date": row.snapshot_date,
        "rainfall_mm": row.rainfall_mm,
        "humidity_pct": row.humidity_pct,
        "temp_min_c": row.temp_min_c,
        "temp_max_c": row.temp_max_c,
    }
