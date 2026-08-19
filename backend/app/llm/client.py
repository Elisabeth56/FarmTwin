"""Thin HTTP client around llama-server.

No smarts: just POST to /completion, parse the JSON, and expose a
last-fenced-block extractor to handle models that echo the schema
template before their real answer.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

import httpx


LLAMA_URL = os.environ.get("FARMTWIN_LLAMA_URL", "http://127.0.0.1:8080/completion")
LLAMA_HEALTH_URL = LLAMA_URL.rsplit("/", 1)[0] + "/health"

_JSON_FENCE_RE = re.compile(r"```json\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def generate(
    prompt: str,
    n_predict: int = 600,
    temperature: float = 0.3,
    stop: Optional[list[str]] = None,
) -> dict:
    """POST to llama-server /completion; return the full JSON response dict.

    Raises httpx.HTTPError on network failure; callers should catch.
    """
    payload: dict[str, Any] = {
        "prompt": prompt,
        "n_predict": n_predict,
        "temperature": temperature,
    }
    if stop:
        payload["stop"] = stop
    resp = httpx.post(LLAMA_URL, json=payload, timeout=300.0)
    resp.raise_for_status()
    return resp.json()


def extract_content(response: dict) -> str:
    return response.get("content", "") or ""


def extract_json_block(content: str) -> Optional[dict]:
    """Return the LAST fenced ```json ... ``` block as a parsed dict.

    Returns None if no block is found or parsing fails.
    """
    if not content:
        return None
    matches = _JSON_FENCE_RE.findall(content)
    if not matches:
        return None
    last = matches[-1].strip()
    try:
        parsed = json.loads(last)
        if isinstance(parsed, dict):
            return parsed
        return None
    except json.JSONDecodeError:
        return None


def health_check() -> bool:
    """GET /health on llama-server. True if 200, False on any failure."""
    try:
        resp = httpx.get(LLAMA_HEALTH_URL, timeout=2.0)
        return resp.status_code == 200
    except Exception:
        return False
