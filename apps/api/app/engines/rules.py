"""Crop rule engine: reads knowledge/crops/*.yaml and turns a planting plus recent readings into
a growth stage and the risks that fire. Pure functions over loaded files; no I/O per call, no LLM.

Rule format (full reference in docs/crop-rules.md):

    risks:
      - id: heavy_rainfall_fungal_risk
        severity: high            # low | medium | high
        urgency: this_week        # immediate | this_week | monitor
        stages: [vegetative]      # omit to apply at every stage
        when: <condition>
        reason: ...
        source: <corpus source_id>

    condition := {any: [condition, ...]} | {all: [condition, ...]} | {not: condition}
               | {observation: {type, min?, max?, within_days?}}
               | {weather: {field, min?, max?, within_days?}}
               | {rule: <id of an earlier risk in the same file>}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from app.config import get_settings

Severity = Literal["low", "medium", "high"]
Urgency = Literal["immediate", "this_week", "monitor"]
WeatherField = Literal["rainfall_mm", "humidity_pct", "temp_max_c", "temp_min_c"]
ObsType = Literal["rainfall", "humidity", "temperature", "pest", "disease", "note"]


# ---- file schema -----------------------------------------------------------------------------


class Stage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    from_day: int
    to_day: int
    description: str


class Risk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    severity: Severity
    urgency: Urgency
    stages: list[str] | None = None
    when: dict[str, Any]
    reason: str
    # shown when the condition holds through absence (a `not`), where no reading explains it
    fact: str | None = None
    source: str


class CropFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    crop: str
    name: str
    sources: list[str] = []
    stages: list[Stage] = []
    risks: list[Risk] = []

    @model_validator(mode="after")
    def check_references(self) -> CropFile:
        stage_ids = {s.id for s in self.stages}
        seen: set[str] = set()
        for risk in self.risks:
            unknown = set(risk.stages or []) - stage_ids
            if self.stages and unknown:
                raise ValueError(f"{self.crop}: risk {risk.id} names unknown stages {sorted(unknown)}")
            _check_condition(risk.when, seen, f"{self.crop}.{risk.id}")
            seen.add(risk.id)
        return self


def _check_condition(cond: dict[str, Any], earlier: set[str], where: str) -> None:
    if len(cond) != 1:
        raise ValueError(f"{where}: each condition has exactly one key, got {sorted(cond)}")
    ((kind, value),) = cond.items()
    if kind in ("any", "all"):
        for c in value:
            _check_condition(c, earlier, where)
    elif kind == "not":
        _check_condition(value, earlier, where)
    elif kind == "observation":
        _ObsCond.model_validate(value)
    elif kind == "weather":
        _WeatherCond.model_validate(value)
    elif kind == "rule":
        if value not in earlier:
            raise ValueError(f"{where}: `rule: {value}` must name a risk defined above it")
    else:
        raise ValueError(f"{where}: unknown condition `{kind}`")


class _ObsCond(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: ObsType
    min: float | None = None
    max: float | None = None
    within_days: int | None = None


class _WeatherCond(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: WeatherField
    min: float | None = None
    max: float | None = None
    within_days: int | None = None


# ---- loading ---------------------------------------------------------------------------------


def _read(path: Path) -> CropFile:
    data = yaml.safe_load(path.read_text())
    try:
        return CropFile.model_validate(data)
    except ValueError as exc:
        raise ValueError(f"{path.name}: {exc}") from exc


@lru_cache
def load_crops(crops_dir: Path | None = None) -> tuple[dict[str, CropFile], CropFile]:
    """Returns (crop files by crop key, the common rules applied to every crop)."""
    folder = crops_dir or get_settings().knowledge_dir / "crops"
    crops = {f.crop: f for f in (_read(p) for p in sorted(folder.glob("[!_]*.yaml")))}
    common = _read(folder / "_common.yaml")
    return crops, common


# ---- stage -----------------------------------------------------------------------------------


def growth_stage(crop: str, planting_date: date, today: date | None = None) -> dict[str, Any]:
    """Current stage, days since planting and harvest window. Raises ValueError for an unknown crop."""
    today = today or date.today()
    crops, _ = load_crops()
    spec = crops.get(crop.lower().strip())
    if spec is None or not spec.stages:
        raise ValueError(f"Unknown crop_type: {crop!r}")

    days = (today - planting_date).days
    total = max(s.to_day for s in spec.stages)
    # the harvest window is the last 10% of the cycle (as in v1)
    window = (planting_date + timedelta(days=int(total * 0.9)), planting_date + timedelta(days=total))

    stage = next((s for s in spec.stages if s.from_day <= days < s.to_day), None)
    if stage:
        label, description = stage.id, stage.description
    elif days < 0:
        label, description = "pre_planting", "Planting date is in the future."
    else:
        label, description = "past_maturity", "Beyond expected harvest window."

    return {
        "stage": label,
        "days_since_planting": days,
        "total_cycle_days": total,
        "expected_harvest_range": window,
        "description": description,
    }


# ---- risks -----------------------------------------------------------------------------------


@dataclass
class RiskFlag:
    name: str
    severity: Severity
    reason: str
    time_sensitivity: Urgency
    supporting_facts: list[str] = field(default_factory=list)
    source: str = ""


@dataclass
class _Readings:
    observations: list[dict[str, Any]]
    weather: dict[str, Any]
    today: date
    fired: dict[str, list[str]] = field(default_factory=dict)


def evaluate(
    crop: str,
    stage: str,
    observations: list[dict[str, Any]],
    weather: dict[str, Any] | None,
    today: date | None = None,
) -> list[RiskFlag]:
    """Runs the crop's rules, then the common ones, and returns every risk that fired, in file order."""
    crops, common = load_crops()
    readings = _Readings(observations or [], weather or {}, today or date.today())
    spec = crops.get(crop.lower().strip())
    flags: list[RiskFlag] = []
    for risk in (spec.risks if spec else []) + common.risks:
        if risk.stages is not None and stage not in risk.stages:
            continue
        holds, facts = _holds(risk.when, readings)
        if not holds:
            continue
        if risk.fact:
            facts = facts + [risk.fact.format(today=readings.today.isoformat())]
        readings.fired[risk.id] = facts
        flags.append(RiskFlag(risk.id, risk.severity, risk.reason, risk.urgency, facts, risk.source))
    return flags


def _holds(cond: dict[str, Any], r: _Readings) -> tuple[bool, list[str]]:
    """Whether the condition holds, plus the readings that made it hold."""
    ((kind, value),) = cond.items()
    if kind == "any":
        results = [_holds(c, r) for c in value]
        return any(ok for ok, _ in results), [f for ok, facts in results if ok for f in facts]
    if kind == "all":
        results = [_holds(c, r) for c in value]
        ok = all(ok for ok, _ in results)
        return ok, [f for _, facts in results for f in facts] if ok else []
    if kind == "not":
        ok, _ = _holds(value, r)
        return not ok, []
    if kind == "rule":
        return value in r.fired, list(r.fired.get(value, []))
    if kind == "observation":
        return _observation(_ObsCond.model_validate(value), r)
    return _weather(_WeatherCond.model_validate(value), r)


def _in_range(v: float | None, lo: float | None, hi: float | None) -> bool:
    if lo is None and hi is None:
        return True
    v = v or 0.0
    return (lo is None or v >= lo) and (hi is None or v <= hi)


def _observation(c: _ObsCond, r: _Readings) -> tuple[bool, list[str]]:
    hits = [
        o
        for o in r.observations
        if o.get("obs_type") == c.type
        and _in_range(o.get("value_numeric"), c.min, c.max)
        and (c.within_days is None or _age(o.get("observed_at"), r.today) in range(0, c.within_days + 1))
    ]
    return bool(hits), [_describe(o) for o in hits]


def _weather(c: _WeatherCond, r: _Readings) -> tuple[bool, list[str]]:
    if not r.weather:
        return False, []
    value = float(r.weather.get(c.field) or 0)
    if not _in_range(value, c.min, c.max):
        return False, []
    taken = r.weather.get("snapshot_date")
    if c.within_days is not None and _age(taken, r.today) not in range(0, c.within_days + 1):
        return False, []
    return True, [f"Weather on {taken}: {_WEATHER_LABELS[c.field]} {value:g}{_WEATHER_UNITS[c.field]}"]


_WEATHER_LABELS = {
    "rainfall_mm": "rainfall",
    "humidity_pct": "humidity",
    "temp_max_c": "max temp",
    "temp_min_c": "min temp",
}
_WEATHER_UNITS = {"rainfall_mm": "mm", "humidity_pct": "%", "temp_max_c": "°C", "temp_min_c": "°C"}


def _as_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None
    return None


def _age(value: Any, today: date) -> int:
    d = _as_date(value)
    return (today - d).days if d else -1


def _describe(o: dict[str, Any]) -> str:
    d = _as_date(o.get("observed_at"))
    when = d.isoformat() if d else "?"
    if o.get("value_numeric") is not None:
        return f"{o['obs_type'].capitalize()} on {when}: {o['value_numeric']:g}{o.get('unit') or ''}"
    return f"{o['obs_type'].capitalize()} report on {when}: {o.get('value_text') or ''}".strip()
