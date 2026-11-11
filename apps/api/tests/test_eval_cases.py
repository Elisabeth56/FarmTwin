import json
from pathlib import Path

from app.config import get_settings
from app.engines.rules import load_crops
from app.rag.corpus import load_corpus

CASES_FILE = Path(__file__).resolve().parents[3] / "evals" / "cases.jsonl"
CASES = [json.loads(line) for line in CASES_FILE.read_text().splitlines() if line]


def test_golden_set_covers_what_adr_024_asks_for():
    assert len(CASES) >= 40
    assert len({c["id"] for c in CASES}) == len(CASES)
    crops = {crop for c in CASES for crop in c["crops"]}
    assert set(load_crops()[0]) <= crops
    tags = {t for c in CASES for t in c["tags"]}
    assert {"unanswerable", "pidgin", "intercrop"} <= tags


def test_expected_sources_exist_in_the_corpus():
    known = {c.frontmatter["source_id"] for c in load_corpus(get_settings().knowledge_dir / "corpus")}
    for case in CASES:
        assert set(case["expected_sources"]) <= known, case["id"]
        assert bool(case["expected_sources"]) == case["answerable"], case["id"]
