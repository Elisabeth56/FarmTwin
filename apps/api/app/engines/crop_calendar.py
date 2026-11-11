"""Growth stage for a planting. Stages come from knowledge/crops/<crop>.yaml via the rule engine."""

from datetime import date
from typing import Any

from app.engines.rules import growth_stage


def compute_growth_stage(crop_type: str, planting_date: date, today: date | None = None) -> dict[str, Any]:
    """Current stage, days since planting, cycle length and harvest window. Raises ValueError for unknown crops."""
    return growth_stage(crop_type, planting_date, today)


def format_stage_summary(result: dict[str, Any]) -> str:
    """One-line human-readable summary of a growth-stage result."""
    stage_label = result["stage"].replace("_", " ").capitalize()
    h_start, h_end = result["expected_harvest_range"]
    return (
        f"{stage_label} stage, day {result['days_since_planting']} of ~{result['total_cycle_days']}, "
        f"expected harvest between {h_start.isoformat()} and {h_end.isoformat()}"
    )
