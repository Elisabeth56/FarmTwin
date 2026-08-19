"""/api/ask — the endpoint that ties the FarmTwin brain together.

Flow:
    1. Load farm + fields + active crop + recent observations + latest weather.
    2. Compute growth stage (deterministic).
    3. Evaluate rule-based risks (deterministic).
    4. Build a compact retrieval query, run KNN, get top-6 chunks.
    5. Assemble a Qwen-chat-template prompt.
    6. Call llama-server /completion.
    7. Extract narrative + parse the last fenced JSON block.
    8. Persist recommendations (with cited chunk ids) and return the response.
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import date, datetime, timedelta
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.engines import crop_calendar, risk_rules, context_assembler
from app.llm import client as llm_client
from app.rag import retriever


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ask", tags=["ask"])

MODEL_NAME = "qwen2.5-3b-instruct-q4_k_m"
CITATION_RE = re.compile(r"\[K(\d+)\]")


class AskRequest(BaseModel):
    farm_id: int
    question: str = Field(..., min_length=3, max_length=500)


class AskResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    narrative: str
    recommendations: list[dict]
    cited_chunks: list[dict]
    model_name: str
    timing_ms: dict
    saved_recommendation_ids: list[int]


def _as_date(v: Any) -> Optional[date]:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return None


@router.post("", response_model=AskResponse)
def ask(payload: AskRequest, db: Session = Depends(get_db)) -> AskResponse:
    t_total_start = time.time()

    farm = db.query(models.Farm).filter(models.Farm.id == payload.farm_id).first()
    if not farm:
        raise HTTPException(404, "farm not found")

    fields = db.query(models.Field).filter(models.Field.farm_id == farm.id).all()
    field_ids = [f.id for f in fields]

    active_crops = []
    if field_ids:
        active_crops = (
            db.query(models.Crop)
            .filter(models.Crop.field_id.in_(field_ids))
            .filter(models.Crop.status == "active")
            .order_by(models.Crop.id.desc())
            .all()
        )

    if not active_crops:
        return AskResponse(
            narrative=(
                "No active crop found for this farm. Add a crop (with a "
                "planting date and status='active') to a field, then ask again."
            ),
            recommendations=[],
            cited_chunks=[],
            model_name=MODEL_NAME,
            timing_ms={"total_ms": int((time.time() - t_total_start) * 1000)},
            saved_recommendation_ids=[],
        )

    crop = active_crops[0]
    field = next((f for f in fields if f.id == crop.field_id), None)
    today = date.today()

    # Growth stage (deterministic).
    if crop.planting_date is None:
        stage_result = {
            "stage": "unknown",
            "days_since_planting": 0,
            "total_cycle_days": 0,
            "expected_harvest_range": (today, today),
            "description": "No planting date recorded.",
        }
    else:
        try:
            stage_result = crop_calendar.compute_growth_stage(
                crop.crop_type, crop.planting_date, today
            )
        except ValueError:
            stage_result = {
                "stage": "unknown",
                "days_since_planting": (today - crop.planting_date).days,
                "total_cycle_days": 0,
                "expected_harvest_range": (crop.planting_date, crop.planting_date),
                "description": f"Unknown crop type: {crop.crop_type}",
            }

    # Recent observations (last 30 days) across all fields.
    cutoff = datetime.combine(today - timedelta(days=30), datetime.min.time())
    obs_rows = []
    if field_ids:
        obs_rows = (
            db.query(models.Observation)
            .filter(models.Observation.field_id.in_(field_ids))
            .filter(models.Observation.observed_at >= cutoff)
            .order_by(models.Observation.observed_at.desc())
            .all()
        )
    recent_obs_dicts = [
        {
            "obs_type": o.obs_type,
            "value_numeric": o.value_numeric,
            "value_text": o.value_text,
            "unit": o.unit,
            "observed_at": _as_date(o.observed_at),
        }
        for o in obs_rows
    ]

    # Latest weather snapshot.
    weather_row = (
        db.query(models.WeatherSnapshot)
        .filter(models.WeatherSnapshot.farm_id == farm.id)
        .order_by(models.WeatherSnapshot.snapshot_date.desc())
        .first()
    )
    latest_weather = None
    if weather_row:
        latest_weather = {
            "rainfall_mm": weather_row.rainfall_mm,
            "humidity_pct": weather_row.humidity_pct,
            "temp_min_c": weather_row.temp_min_c,
            "temp_max_c": weather_row.temp_max_c,
            "snapshot_date": weather_row.snapshot_date,
        }

    # Risk flags (deterministic).
    flags = risk_rules.evaluate_risks(
        crop.crop_type,
        stage_result["stage"],
        recent_obs_dicts,
        latest_weather,
        today=today,
    )

    # Farm facts for the prompt.
    h_start, h_end = stage_result["expected_harvest_range"]
    farm_facts: dict[str, Any] = {
        "farm_name": farm.name,
        "region": farm.region,
        "area_hectares": farm.area_hectares,
        "field_name": field.name if field else None,
        "soil_type": field.soil_type if field else None,
        "crop": crop.crop_type,
        "variety": crop.variety,
        "planting_date": crop.planting_date.isoformat() if crop.planting_date else None,
        "growth_stage": stage_result["stage"],
        "days_since_planting": stage_result["days_since_planting"],
        "expected_harvest_between": f"{h_start.isoformat()} and {h_end.isoformat()}",
        "today": today.isoformat(),
        "latest_weather": (
            {
                "snapshot_date": latest_weather["snapshot_date"].isoformat() if latest_weather else None,
                "rainfall_mm": latest_weather["rainfall_mm"] if latest_weather else None,
                "humidity_pct": latest_weather["humidity_pct"] if latest_weather else None,
                "temp_min_c": latest_weather["temp_min_c"] if latest_weather else None,
                "temp_max_c": latest_weather["temp_max_c"] if latest_weather else None,
            } if latest_weather else None
        ),
        "recent_observations": [
            {
                "date": o["observed_at"].isoformat() if o["observed_at"] else None,
                "type": o["obs_type"],
                "value": o["value_numeric"] if o["value_numeric"] is not None else o["value_text"],
                "unit": o["unit"],
            }
            for o in recent_obs_dicts[:12]
        ],
    }

    # Retrieval.
    query = retriever.build_query(
        crop_type=crop.crop_type,
        growth_stage=stage_result["stage"],
        region=farm.region or "",
        risk_flags=flags,
        user_question=payload.question,
    )
    chunks = retriever.retrieve_chunks(query, top_k=6, db_session=db)

    # Prompt assembly.
    prompt = context_assembler.assemble_prompt(
        farm_facts=farm_facts,
        risk_flags=flags,
        chunks=chunks,
        user_question=payload.question,
    )

    # LLM call.
    t_llm_start = time.time()
    try:
        response = llm_client.generate(prompt, n_predict=600, temperature=0.3)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.HTTPError) as e:
        logger.warning("llama-server unreachable: %s", e)
        raise HTTPException(
            status_code=503,
            detail="Local model not available. Start llama-server first.",
        )
    t_llm_end = time.time()

    content = llm_client.extract_content(response)
    parsed = llm_client.extract_json_block(content)

    recommendations: list[dict] = []
    if parsed and isinstance(parsed.get("recommendations"), list):
        recommendations = [r for r in parsed["recommendations"] if isinstance(r, dict)]
    else:
        logger.warning("ask: no parseable JSON block in model output")

    # Map [K#] citations in the narrative to real chunk_ids.
    cited_indices = {int(m) for m in CITATION_RE.findall(content)}
    cited_chunk_ids: list[int] = []
    cited_chunks_meta: list[dict] = []
    for idx in sorted(cited_indices):
        if 1 <= idx <= len(chunks):
            ch = chunks[idx - 1]
            cited_chunk_ids.append(ch["chunk_id"])
            cited_chunks_meta.append({
                "citation": f"K{idx}",
                "chunk_id": ch["chunk_id"],
                "source_org": ch.get("source_org"),
                "source_title": ch.get("source_title"),
                "chunk_title": ch.get("chunk_title"),
                "region": ch.get("region"),
                "crop": ch.get("crop"),
                "topics": ch.get("topics"),
                "distance": ch.get("distance"),
            })

    # Persist recommendations.
    saved_ids: list[int] = []
    for rec in recommendations:
        urgency = rec.get("when_urgency")
        priority_str = (rec.get("priority") or "").lower()
        priority_int = {"high": 1, "medium": 2, "low": 3}.get(priority_str)
        row = models.Recommendation(
            farm_id=farm.id,
            field_id=field.id if field else None,
            what=str(rec.get("what") or ""),
            why=str(rec.get("why") or ""),
            when_urgency=urgency if isinstance(urgency, str) else None,
            risk_if_ignored=str(rec.get("risk_if_ignored") or ""),
            priority=priority_int,
            cited_chunk_ids=json.dumps(cited_chunk_ids) if cited_chunk_ids else None,
            model_name=MODEL_NAME,
        )
        db.add(row)
        db.flush()
        saved_ids.append(row.id)
    db.commit()

    timings = response.get("timings", {}) if isinstance(response, dict) else {}
    timing_ms = {
        "prompt_ms": int(timings.get("prompt_ms", 0)),
        "generation_ms": int(timings.get("predicted_ms", 0)),
        "llm_wallclock_ms": int((t_llm_end - t_llm_start) * 1000),
        "total_ms": int((time.time() - t_total_start) * 1000),
    }

    return AskResponse(
        narrative=content,
        recommendations=recommendations,
        cited_chunks=cited_chunks_meta,
        model_name=MODEL_NAME,
        timing_ms=timing_ms,
        saved_recommendation_ids=saved_ids,
    )
