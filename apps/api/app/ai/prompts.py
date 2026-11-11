"""Versioned prompt files. A prompt change is a new version folder, so logs and eval results
always say which wording produced an answer."""

from functools import lru_cache
from pathlib import Path

PROMPTS = Path(__file__).parent / "prompts"
ASK_VERSION = "ask/v2"


@lru_cache
def load(version: str, name: str) -> str:
    return (PROMPTS / version / f"{name}.md").read_text(encoding="utf-8").strip()
