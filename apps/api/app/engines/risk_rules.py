"""Rule-based risks for a planting. Rules live in knowledge/crops/*.yaml; see app/engines/rules.py."""

from datetime import date
from typing import Any

from app.engines.rules import RiskFlag, evaluate

__all__ = ["RiskFlag", "evaluate_risks", "format_risk_summary"]


def evaluate_risks(
    crop_type: str,
    growth_stage: str,
    recent_observations: list[dict[str, Any]],
    latest_weather: dict[str, Any] | None,
    today: date | None = None,
) -> list[RiskFlag]:
    """Every risk that fires for this crop at this stage, with the readings behind it."""
    return evaluate(crop_type, growth_stage, recent_observations, latest_weather, today)


def format_risk_summary(flags: list[RiskFlag]) -> str:
    """Compact multi-line summary suitable for prompt inclusion."""
    if not flags:
        return "No rule-based risks fired for the current farm state."
    lines: list[str] = []
    for f in flags:
        lines.append(f"- [{f.severity.upper()} / {f.time_sensitivity}] {f.name}: {f.reason}")
        lines.extend(f"    • {fact}" for fact in f.supporting_facts)
    return "\n".join(lines)
