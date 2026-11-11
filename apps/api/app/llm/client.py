"""Thin HTTP client around llama-server.

No smarts: just POST to /completion, parse the JSON, and expose a
last-fenced-block extractor to handle models that echo the schema
template before their real answer.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, AsyncGenerator, Optional

import httpx


logger = logging.getLogger(__name__)


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


async def stream_generate(
    prompt: str,
    n_predict: int = 600,
    temperature: float = 0.3,
    stop: Optional[list[str]] = None,
) -> AsyncGenerator[dict, None]:
    """Stream tokens from llama-server.

    Yields dicts of the following shapes:
      - {"type": "token", "content": str}
      - {"type": "done", "timings": dict}
      - {"type": "error", "message": str}
    """
    payload: dict[str, Any] = {
        "prompt": prompt,
        "n_predict": n_predict,
        "temperature": temperature,
        "stream": True,
    }
    if stop:
        payload["stop"] = stop

    timeout = httpx.Timeout(600.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", LLAMA_URL, json=payload) as resp:
                if resp.status_code >= 400:
                    body = await resp.aread()
                    yield {
                        "type": "error",
                        "message": (
                            f"llama-server returned {resp.status_code}: "
                            f"{body.decode('utf-8', errors='replace')[:300]}"
                        ),
                    }
                    return

                async for raw_line in resp.aiter_lines():
                    if not raw_line:
                        continue
                    line = raw_line.strip()
                    if not line.startswith("data:"):
                        continue
                    data_str = line[len("data:"):].strip()
                    if not data_str:
                        continue
                    try:
                        event = json.loads(data_str)
                    except json.JSONDecodeError:
                        logger.warning("stream_generate: bad JSON line: %r", data_str[:120])
                        continue

                    content_piece = event.get("content", "")
                    if content_piece:
                        yield {"type": "token", "content": content_piece}

                    if event.get("stop"):
                        yield {
                            "type": "done",
                            "timings": event.get("timings", {}) or {},
                        }
                        return
    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        logger.warning("stream_generate: connect failed: %s", e)
        yield {
            "type": "error",
            "message": "Local model not available. Start llama-server first.",
        }
    except httpx.ReadTimeout as e:
        logger.warning("stream_generate: read timeout: %s", e)
        yield {
            "type": "error",
            "message": "Model took too long to respond.",
        }
    except httpx.HTTPError as e:
        logger.warning("stream_generate: http error: %s", e)
        yield {
            "type": "error",
            "message": f"llama-server HTTP error: {e}",
        }
    except Exception as e:  # noqa: BLE001
        logger.exception("stream_generate: unexpected error")
        yield {"type": "error", "message": f"Unexpected error: {e}"}


def health_check() -> bool:
    """GET /health on llama-server. True if 200, False on any failure."""
    try:
        resp = httpx.get(LLAMA_HEALTH_URL, timeout=2.0)
        return resp.status_code == 200
    except Exception:
        return False
