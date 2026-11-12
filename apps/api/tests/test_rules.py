import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.engines.rules import CropFile, evaluate, growth_stage, load_crops

# v1 parity holds for maize only; the other crops got sourced calendars and rules in #9
CASES = [
    c
    for c in json.loads((Path(__file__).parent / "fixtures" / "v1_engine_cases.json").read_text())
    if c["crop"] == "maize"
]
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
        (r["name"], r["severity"], r["time_sensitivity"], r["facts"])
        for r in case["expected_risks"]
        # one intended change from v1: no rain data on record is no longer a dry spell
        if not (r["name"] == "moisture_stress_dry_period" and not _has_rain_data(case))
    )
    assert got == want


def _has_rain_data(case) -> bool:
    return any(o["obs_type"] == "rainfall" for o in case["observations"]) or (
        bool(case["weather"]) and case["weather"].get("rainfall_mm") is not None
    )


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
    assert "active_pest_pressure" in names(evaluate("cassava", "bulking", [pest], None, TODAY))


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
            if risk.threshold_source:
                assert risk.threshold_source in known, f"{spec.crop}.{risk.id}"
        for source in spec.sources:
            assert source in known, f"{spec.crop} lists unknown source {source}"


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


def pest(days_ago=0):
    return {
        "obs_type": "pest",
        "value_text": "insects",
        "observed_at": (TODAY - timedelta(days=days_ago)).isoformat(),
    }


@pytest.mark.parametrize("crop", ["maize", "cassava", "yam", "sorghum", "rice", "cowpea"])
def test_every_supported_crop_has_a_calendar(crop):
    stage = growth_stage(crop, TODAY - timedelta(days=20), TODAY)
    assert stage["stage"] not in ("pre_planting", "past_maturity")


def test_rice_stages_follow_faro_44():
    planted = TODAY - timedelta(days=60)
    stage = growth_stage("rice", planted, TODAY)
    assert stage["stage"] == "reproductive"
    assert stage["total_cycle_days"] == 110


def test_damp_weather_raises_blast_risk_on_young_rice():
    assert "damp_weather_blast" in names(evaluate("rice", "vegetative", [], weather(humidity_pct=85), TODAY))
    assert "damp_weather_blast" not in names(
        evaluate("rice", "ripening", [], weather(humidity_pct=85), TODAY)
    )


def test_dry_spell_at_a_critical_rice_stage():
    assert "water_shortage_critical_stage" in names(
        evaluate("rice", "reproductive", [rain(2, 15)], None, TODAY)
    )
    assert "water_shortage_critical_stage" not in names(evaluate("rice", "reproductive", [], None, TODAY))
    assert "water_shortage_critical_stage" not in names(
        evaluate("rice", "reproductive", [rain(20, 3)], None, TODAY)
    )


def test_dry_weather_on_young_cassava_flags_mites_and_mealybug():
    dry = [rain(0, 12)]
    assert "dry_weather_mite_mealybug" in names(evaluate("cassava", "root_initiation", dry, None, TODAY))
    assert "dry_weather_mite_mealybug" not in names(evaluate("cassava", "bulking", dry, None, TODAY))


def test_no_rain_data_is_not_a_dry_spell():
    assert "dry_weather_mite_mealybug" not in names(evaluate("cassava", "root_initiation", [], None, TODAY))
    assert "moisture_stress_dry_period" not in names(evaluate("maize", "vegetative", [], None, TODAY))
    zero_rain_weather = weather(rainfall_mm=0)
    assert "moisture_stress_dry_period" in names(
        evaluate("maize", "vegetative", [], zero_rain_weather, TODAY)
    )


def test_heavy_rain_on_cassava():
    flags = names(evaluate("cassava", "bulking", [rain(60, 1)], None, TODAY))
    assert {"wet_weather_blight_anthracnose", "waterlogging_root_rot"} <= flags


def test_heavy_rain_spreads_yam_anthracnose():
    assert "rain_splash_anthracnose" in names(evaluate("yam", "growing", [], weather(rainfall_mm=55), TODAY))
    assert "rain_splash_anthracnose" not in names(evaluate("yam", "growing", [rain(20, 1)], None, TODAY))


def test_pests_in_the_sorghum_shoot_fly_window():
    assert "pests_in_shoot_fly_window" in names(evaluate("sorghum", "seedling", [pest()], None, TODAY))
    assert "pests_in_shoot_fly_window" not in names(evaluate("sorghum", "growing", [pest()], None, TODAY))


def test_pests_at_cowpea_flowering():
    flags = evaluate("cowpea", "flowering", [pest(2)], None, TODAY)
    assert {"pests_at_flowering_or_podding", "active_pest_pressure"} <= names(flags)
    assert "pests_at_flowering_or_podding" not in names(evaluate("cowpea", "seedling", [pest()], None, TODAY))
