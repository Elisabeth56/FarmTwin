"""Deterministic crop growth stage calculator.

Given a crop type and planting date, returns the current growth stage,
expected harvest window, and a human-readable summary. Pure functions,
no I/O and no LLM.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional


MAIZE_LIFECYCLE: dict[str, tuple[str, int, int, str]] = {
    "germination": ("germination", 0, 7, "Seed absorbs water and emerges."),
    "seedling": ("seedling", 7, 21, "Early leaf development, root establishment."),
    "vegetative": ("vegetative", 21, 60, "Rapid leaf and stalk growth."),
    "flowering": ("flowering", 60, 75, "Tasseling and silking; highly water-sensitive."),
    "grain_filling": ("grain_filling", 75, 105, "Kernel development and dry matter accumulation."),
    "maturity": ("maturity", 105, 120, "Physiological maturity; drying down for harvest."),
}

RICE_LIFECYCLE: dict[str, tuple[str, int, int, str]] = {
    "growing": ("growing", 0, 100, "Vegetative through reproductive growth."),
    "maturity": ("maturity", 100, 150, "Grain filling and drying to harvest."),
}

CASSAVA_LIFECYCLE: dict[str, tuple[str, int, int, str]] = {
    "growing": ("growing", 0, 270, "Canopy establishment and tuber bulking."),
    "maturity": ("maturity", 270, 450, "Tubers ready for harvest window."),
}

YAM_LIFECYCLE: dict[str, tuple[str, int, int, str]] = {
    "growing": ("growing", 0, 270, "Vine growth and tuber development."),
    "maturity": ("maturity", 270, 330, "Tubers ready for harvest window."),
}

LIFECYCLES: dict[str, dict[str, tuple[str, int, int, str]]] = {
    "maize": MAIZE_LIFECYCLE,
    "rice": RICE_LIFECYCLE,
    "cassava": CASSAVA_LIFECYCLE,
    "yam": YAM_LIFECYCLE,
}


def compute_growth_stage(
    crop_type: str,
    planting_date: date,
    today: Optional[date] = None,
) -> dict:
    """Return current growth stage info for a crop.

    Raises ValueError if crop_type is not recognized.
    """
    if today is None:
        today = date.today()

    key = crop_type.lower().strip()
    lifecycle = LIFECYCLES.get(key)
    if lifecycle is None:
        raise ValueError(f"Unknown crop_type: {crop_type!r}")

    days = (today - planting_date).days
    total_days = max(stage[2] for stage in lifecycle.values())
    # Harvest window: last 10% of the cycle through the max day.
    harvest_start = planting_date + timedelta(days=int(total_days * 0.9))
    harvest_end = planting_date + timedelta(days=total_days)

    matched_stage = None
    matched_desc = ""
    for _name, (label, min_d, max_d, desc) in lifecycle.items():
        if min_d <= days < max_d:
            matched_stage = label
            matched_desc = desc
            break

    if matched_stage is None:
        if days < 0:
            matched_stage = "pre_planting"
            matched_desc = "Planting date is in the future."
        else:
            matched_stage = "past_maturity"
            matched_desc = "Beyond expected harvest window."

    return {
        "stage": matched_stage,
        "days_since_planting": days,
        "total_cycle_days": total_days,
        "expected_harvest_range": (harvest_start, harvest_end),
        "description": matched_desc,
    }


def format_stage_summary(result: dict) -> str:
    """One-line human-readable summary of a growth-stage result."""
    stage_label = result["stage"].replace("_", " ").capitalize()
    days = result["days_since_planting"]
    cycle = result["total_cycle_days"]
    h_start, h_end = result["expected_harvest_range"]
    return (
        f"{stage_label} stage, day {days} of ~{cycle}, "
        f"expected harvest between {h_start.isoformat()} and {h_end.isoformat()}"
    )
