"""Deterministic risk evaluator.

Given a crop, its growth stage, recent observations, and the latest weather
snapshot, emit a set of RiskFlags. No I/O, no LLM. All rules are transparent
and cite the specific values that triggered them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal

Severity = Literal["low", "medium", "high"]
TimeSensitivity = Literal["immediate", "this_week", "monitor"]


@dataclass
class RiskFlag:
    name: str
    severity: Severity
    reason: str
    time_sensitivity: TimeSensitivity
    supporting_facts: list[str] = field(default_factory=list)


def _obs_date(obs: dict) -> date | None:
    v = obs.get("observed_at")
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v).date()
        except ValueError:
            return None
    return None


def _within_days(obs: dict, days: int, today: date) -> bool:
    d = _obs_date(obs)
    return d is not None and 0 <= (today - d).days <= days


def evaluate_risks(
    crop_type: str,
    growth_stage: str,
    recent_observations: list[dict],
    latest_weather: dict | None,
    today: date | None = None,
) -> list[RiskFlag]:
    """Run all rules and return the flags that fired.

    - crop_type: lowercase crop key (e.g. "maize").
    - growth_stage: stage label from crop_calendar.
    - recent_observations: list of dicts with obs_type / value_numeric / value_text /
      observed_at / unit.
    - latest_weather: dict with rainfall_mm / humidity_pct / temp_min_c / temp_max_c /
      snapshot_date, or None.
    """
    if today is None:
        today = date.today()

    crop = (crop_type or "").lower().strip()
    stage = (growth_stage or "").lower().strip()
    obs_list = recent_observations or []
    weather = latest_weather or {}

    flags: list[RiskFlag] = []

    heavy_rain_obs = [
        o
        for o in obs_list
        if o.get("obs_type") == "rainfall"
        and (o.get("value_numeric") or 0) >= 50
        and _within_days(o, 5, today)
    ]
    weather_rain = float(weather.get("rainfall_mm") or 0)
    weather_humidity = float(weather.get("humidity_pct") or 0)
    weather_date = weather.get("snapshot_date")

    rule1_fires = crop == "maize" and stage == "vegetative" and (heavy_rain_obs or weather_rain >= 50)
    rule2_fires = crop == "maize" and stage in {"vegetative", "flowering"} and (weather_humidity >= 80)

    # Rule 1: heavy recent rainfall on vegetative maize.
    if rule1_fires:
        facts: list[str] = []
        for o in heavy_rain_obs:
            d = _obs_date(o)
            facts.append(
                f"Rainfall observation on {d.isoformat() if d else '?'}: "
                f"{o.get('value_numeric')}{o.get('unit') or 'mm'}"
            )
        if weather_rain >= 50:
            facts.append(f"Latest weather ({weather_date}): {weather_rain}mm rainfall")
        flags.append(
            RiskFlag(
                name="heavy_rainfall_fungal_risk",
                severity="high",
                reason=(
                    "Heavy recent rainfall on vegetative maize creates ideal "
                    "conditions for fungal foliar diseases."
                ),
                time_sensitivity="this_week",
                supporting_facts=facts,
            )
        )

    # Rule 2: sustained high humidity on vegetative/flowering maize.
    if rule2_fires:
        facts = [f"Latest weather ({weather_date}): humidity {weather_humidity}%"]
        flags.append(
            RiskFlag(
                name="high_humidity_foliar_pressure",
                severity="medium",
                reason=(
                    "Sustained humidity at or above 80% on maize in the "
                    "vegetative/flowering window elevates foliar disease pressure."
                ),
                time_sensitivity="this_week",
                supporting_facts=facts,
            )
        )

    # Rule 3: combined rain + humidity → flagship fungal outbreak risk.
    if rule1_fires and rule2_fires:
        combined_facts: list[str] = []
        for o in heavy_rain_obs:
            d = _obs_date(o)
            combined_facts.append(
                f"Rainfall on {d.isoformat() if d else '?'}: "
                f"{o.get('value_numeric')}{o.get('unit') or 'mm'}"
            )
        if weather_rain >= 50:
            combined_facts.append(f"Latest weather rainfall: {weather_rain}mm on {weather_date}")
        combined_facts.append(f"Latest weather humidity: {weather_humidity}% on {weather_date}")
        flags.append(
            RiskFlag(
                name="combined_rain_humidity_outbreak_risk",
                severity="high",
                reason=(
                    "Heavy rainfall combined with sustained high humidity on "
                    "vegetative maize is the classic trigger for a fungal "
                    "disease outbreak; act before symptoms appear."
                ),
                time_sensitivity="immediate",
                supporting_facts=combined_facts,
            )
        )

    # Rule 4: extended dry period on vegetative/flowering maize.
    if crop == "maize" and stage in {"vegetative", "flowering"}:
        recent_wet = [
            o
            for o in obs_list
            if o.get("obs_type") == "rainfall"
            and (o.get("value_numeric") or 0) >= 10
            and _within_days(o, 10, today)
        ]
        weather_recent_wet = False
        if weather_date is not None and weather_rain >= 5:
            w_date = weather_date
            if isinstance(w_date, str):
                try:
                    w_date = datetime.fromisoformat(w_date).date()
                except ValueError:
                    w_date = None
            if isinstance(w_date, datetime):
                w_date = w_date.date()
            if isinstance(w_date, date) and (today - w_date).days <= 10:
                weather_recent_wet = True
        if not recent_wet and not weather_recent_wet:
            flags.append(
                RiskFlag(
                    name="moisture_stress_dry_period",
                    severity="medium",
                    reason=(
                        "No significant rainfall recorded in the last 10 days "
                        "during a moisture-sensitive stage; yield loss risk if "
                        "the dry period continues."
                    ),
                    time_sensitivity="this_week",
                    supporting_facts=[
                        f"No rainfall observations ≥10mm in last 10 days as of {today.isoformat()}"
                    ],
                )
            )

    # Rule 5: pest observation in last 7 days.
    pest_obs = [o for o in obs_list if o.get("obs_type") == "pest" and _within_days(o, 7, today)]
    if pest_obs:
        facts = []
        for o in pest_obs:
            d = _obs_date(o)
            note = o.get("value_text") or ""
            facts.append(f"Pest report on {d.isoformat() if d else '?'}: {note}".strip())
        flags.append(
            RiskFlag(
                name="active_pest_pressure",
                severity="high",
                reason="Recent farmer-reported pest activity requires prompt scouting and action.",
                time_sensitivity="immediate",
                supporting_facts=facts,
            )
        )

    # Rule 6: disease observation in last 7 days.
    disease_obs = [o for o in obs_list if o.get("obs_type") == "disease" and _within_days(o, 7, today)]
    if disease_obs:
        facts = []
        for o in disease_obs:
            d = _obs_date(o)
            note = o.get("value_text") or ""
            facts.append(f"Disease report on {d.isoformat() if d else '?'}: {note}".strip())
        flags.append(
            RiskFlag(
                name="active_disease_pressure",
                severity="high",
                reason="Recent farmer-reported disease symptoms require field inspection and possible intervention.",
                time_sensitivity="immediate",
                supporting_facts=facts,
            )
        )

    # Rule 7: heat stress at flowering (temperature ≥ 35C during flowering).
    if crop == "maize" and stage == "flowering":
        t_max = weather.get("temp_max_c")
        if t_max is not None and float(t_max) >= 35:
            flags.append(
                RiskFlag(
                    name="heat_stress_at_flowering",
                    severity="high",
                    reason=(
                        "Air temperature ≥35°C during flowering can impair "
                        "pollination and reduce grain set."
                    ),
                    time_sensitivity="this_week",
                    supporting_facts=[f"Latest weather ({weather_date}): max temp {t_max}°C"],
                )
            )

    return flags


def format_risk_summary(flags: list[RiskFlag]) -> str:
    """Compact multi-line summary suitable for prompt inclusion."""
    if not flags:
        return "No rule-based risks fired for the current farm state."
    lines: list[str] = []
    for f in flags:
        lines.append(f"- [{f.severity.upper()} / {f.time_sensitivity}] {f.name}: {f.reason}")
        for fact in f.supporting_facts:
            lines.append(f"    • {fact}")
    return "\n".join(lines)
