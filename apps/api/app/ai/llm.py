"""The one place FarmTwin talks to the local model (ADR-020).

llama-server's OpenAI-compatible `/v1/chat/completions` applies the chat template stored in the
GGUF file, so swapping models is a settings change. Errors are raised as AppError (or yielded as
error events when streaming) with the shared codes.
"""

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import httpx

from app.config import get_settings
from app.errors import MODEL_TIMEOUT, MODEL_UNAVAILABLE, AppError

logger = logging.getLogger(__name__)

TIMEOUT = httpx.Timeout(300.0, connect=5.0)


@dataclass
class Completion:
    content: str
    timings: dict = field(default_factory=dict)


def _url(path: str) -> str:
    # the supervisor knows the port when it started llama-server; otherwise it's llama_url
    from app.ai.server import supervisor

    return supervisor.url + path


def _body(messages: list[dict], max_tokens: int, temperature: float, stream: bool) -> dict:
    return {
        "model": get_settings().llm_model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream,
    }


def generate(messages: list[dict], max_tokens: int = 600, temperature: float = 0.3) -> Completion:
    """Returns the whole answer. Raises AppError model_unavailable / model_timeout."""
    try:
        resp = httpx.post(
            _url("/v1/chat/completions"),
            json=_body(messages, max_tokens, temperature, stream=False),
            timeout=TIMEOUT,
            trust_env=False,  # llama-server is local; a system proxy must not intercept it
        )
        resp.raise_for_status()
    except httpx.TimeoutException as exc:
        if isinstance(exc, httpx.ConnectTimeout):
            raise AppError(503, "model_unavailable", MODEL_UNAVAILABLE) from exc
        raise AppError(504, "model_timeout", MODEL_TIMEOUT) from exc
    except httpx.HTTPError as exc:
        logger.warning("llama-server request failed: %s", exc)
        raise AppError(503, "model_unavailable", MODEL_UNAVAILABLE) from exc

    data = resp.json()
    content = data["choices"][0]["message"].get("content") or ""
    return Completion(content, data.get("timings") or {})


async def stream(
    messages: list[dict], max_tokens: int = 600, temperature: float = 0.3
) -> AsyncIterator[dict]:
    """Yields {"type": "token", "content"}, then {"type": "done", "timings"} or {"type": "error", "code", "message"}."""
    timings: dict = {}
    try:
        async with (
            httpx.AsyncClient(timeout=TIMEOUT, trust_env=False) as client,
            client.stream(
                "POST",
                _url("/v1/chat/completions"),
                json=_body(messages, max_tokens, temperature, stream=True),
            ) as resp,
        ):
            if resp.status_code >= 400:
                body = (await resp.aread()).decode("utf-8", errors="replace")[:300]
                logger.warning("llama-server returned %s: %s", resp.status_code, body)
                yield {"type": "error", "code": "model_unavailable", "message": MODEL_UNAVAILABLE}
                return

            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    logger.warning("bad stream line: %r", data[:120])
                    continue
                # llama-server adds its timings to the final chunk
                timings = event.get("timings") or timings
                for choice in event.get("choices") or []:
                    piece = (choice.get("delta") or {}).get("content")
                    if piece:
                        yield {"type": "token", "content": piece}
    except (httpx.ConnectError, httpx.ConnectTimeout):
        yield {"type": "error", "code": "model_unavailable", "message": MODEL_UNAVAILABLE}
        return
    except httpx.ReadTimeout:
        yield {"type": "error", "code": "model_timeout", "message": MODEL_TIMEOUT}
        return
    except httpx.HTTPError as exc:
        logger.warning("stream failed: %s", exc)
        yield {"type": "error", "code": "model_unavailable", "message": MODEL_UNAVAILABLE}
        return
    yield {"type": "done", "timings": timings}


def health() -> bool:
    try:
        return httpx.get(_url("/health"), timeout=2.0, trust_env=False).status_code == 200
    except httpx.HTTPError:
        return False
