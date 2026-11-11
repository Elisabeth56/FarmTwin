import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.engines.rules import CropFile, evaluate, growth_stage, load_crops

CASES = json.loads((Path(__file__).parent / "fixtures" / "v1_engine_cases.json").read_text())
TODAY = date(2026, 7, 15)


@pytest.mark.parametrize("case", CASES, ids=[c["case"] for c in CASES])
def test_matches_the_v1_engine(case):
    today = date.fromisoformat(case["today"])
    stage = growth_stage(case["crop"], date.fromisoformat(case["planting_date"]), today)
    expected = case["expected_stage"]
    assert stage["stage"] == expected["stage"]
    assert stage["days_since_planting"] == expected["days_since_planting"]
    assert stage["total_cycle_days"] == expected["total_cycle_days"]
    assert [d.isoformat() for d in stage["expected_harvest_range"]] == expected["harvest"]

    flags = evaluate(case["crop"], stage["stage"], case["observations"], case["weather"], today)
    got = sorted((f.name, f.severity, f.time_sensitivity, len(f.supporting_facts)) for f in flags)
    want = sorted(
        (r["name"], r["severity"], r["time_sensitivity"], r["facts"]) for r in case["expected_risks"]
    )
    assert got == want


def rain(mm, days_ago):
    return {
        "obs_type": "rainfall",
        "value_numeric": mm,
        "unit": "mm",
        "observed_at": (TODAY - timedelta(days=days_ago)).isoformat(),
    }


def weather(**values):
    return {"snapshot_date": TODAY.isoformat(), **values}


def names(flags):
    return {f.name for f in flags}


def test_heavy_rain_on_vegetative_maize():
    flags = evaluate("maize", "vegetative", [rain(65, 2)], None, TODAY)
    assert "heavy_rainfall_fungal_risk" in names(flags)
    flag = next(f for f in flags if f.name == "heavy_rainfall_fungal_risk")
    assert flag.supporting_facts == [f"Rainfall on {(TODAY - timedelta(days=2)).isoformat()}: 65mm"]
    assert flag.source == "cimmyt_maize_disease_overview"


def test_heavy_rain_outside_five_days_does_not_count():
    assert "heavy_rainfall_fungal_risk" not in names(
        evaluate("maize", "vegetative", [rain(65, 6)], None, TODAY)
    )


def test_high_humidity_at_flowering():
    assert "high_humidity_foliar_pressure" in names(
        evaluate("maize", "flowering", [rain(20, 1)], weather(humidity_pct=85), TODAY)
    )


def test_rain_and_humidity_together_raise_the_outbreak_risk():
    flags = evaluate("maize", "vegetative", [rain(65, 1)], weather(humidity_pct=86), TODAY)
    combined = next(f for f in flags if f.name == "combined_rain_humidity_outbreak_risk")
    assert combined.time_sensitivity == "immediate"
    assert len(combined.supporting_facts) == 2


def test_dry_spell_on_vegetative_maize():
    flags = evaluate("maize", "vegetative", [rain(4, 3)], None, TODAY)
    dry = next(f for f in flags if f.name == "moisture_stress_dry_period")
    assert dry.supporting_facts == [
        f"No rainfall observations ≥10mm in last 10 days as of {TODAY.isoformat()}"
    ]


def test_recent_weather_rain_ends_the_dry_spell():
    assert "moisture_stress_dry_period" not in names(
        evaluate("maize", "vegetative", [], weather(rainfall_mm=6), TODAY)
    )


def test_heat_only_matters_at_flowering():
    hot = weather(temp_max_c=36, rainfall_mm=12)
    assert "heat_stress_at_flowering" in names(evaluate("maize", "flowering", [], hot, TODAY))
    assert "heat_stress_at_flowering" not in names(evaluate("maize", "grain_filling", [], hot, TODAY))


def test_pest_reports_apply_to_every_crop():
    pest = {"obs_type": "pest", "value_text": "mealybugs on shoot tips", "observed_at": TODAY.isoformat()}
    assert "active_pest_pressure" in names(evaluate("cassava", "growing", [pest], None, TODAY))


def test_disease_reports_older_than_a_week_are_ignored():
    old = {
        "obs_type": "disease",
        "value_text": "leaf spots",
        "observed_at": (TODAY - timedelta(days=8)).isoformat(),
    }
    assert "active_disease_pressure" not in names(evaluate("maize", "seedling", [old], None, TODAY))


def test_unknown_crop_has_no_stage():
    with pytest.raises(ValueError):
        growth_stage("cocoa", TODAY)


def test_every_rule_cites_a_corpus_source():
    corpus = Path(__file__).resolve().parents[3] / "knowledge" / "corpus"
    known = {
        line.split(":", 1)[1].strip()
        for p in corpus.glob("*.md")
        for line in p.read_text().splitlines()
        if line.startswith("source_id:")
    }
    crops, common = load_crops()
    for spec in [*crops.values(), common]:
        for risk in spec.risks:
            assert risk.source in known, f"{spec.crop}.{risk.id} cites unknown source {risk.source}"


@pytest.mark.parametrize(
    "bad, message",
    [
        (
            {
                "crop": "x",
                "name": "X",
                "risks": [
                    {
                        "id": "a",
                        "severity": "high",
                        "urgency": "monitor",
                        "when": {"rule": "b"},
                        "reason": "r",
                        "source": "s",
                    }
                ],
            },
            "defined above",
        ),
        (
            {
                "crop": "x",
                "name": "X",
                "risks": [
                    {
                        "id": "a",
                        "severity": "high",
                        "urgency": "monitor",
                        "when": {"soil": {}},
                        "reason": "r",
                        "source": "s",
                    }
                ],
            },
            "unknown condition",
        ),
        (
            {
                "crop": "x",
                "name": "X",
                "stages": [{"id": "s1", "from_day": 0, "to_day": 9, "description": "d"}],
                "risks": [
                    {
                        "id": "a",
                        "severity": "high",
                        "urgency": "monitor",
                        "stages": ["s2"],
                        "when": {"weather": {"field": "humidity_pct", "min": 1}},
                        "reason": "r",
                        "source": "s",
                    }
                ],
            },
            "unknown stages",
        ),
    ],
)
def test_bad_rule_files_are_rejected(bad, message):
    with pytest.raises(ValueError, match=message):
        CropFile.model_validate(bad)
