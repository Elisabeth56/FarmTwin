"""Thin subprocess wrapper around whisper.cpp's `whisper-cli` binary.

The wrapper is intentionally minimal: one function that takes a WAV path
and returns a transcript dict. Audio format conversion is handled upstream
(see `app/api/transcribe.py`) so this module only deals with the whisper
invocation itself.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path


WHISPER_BIN = os.environ.get(
    "FARMTWIN_WHISPER_BIN",
    "/Users/macbookpro/dev/tools/whisper.cpp/build/bin/whisper-cli",
)
WHISPER_MODEL = os.environ.get(
    "FARMTWIN_WHISPER_MODEL",
    "/Users/macbookpro/farmtwin-models/ggml-base-q5_1.bin",
)

# Whisper.cpp doesn't have a Nigerian Pidgin language code; route both
# "en" and "pidgin" through the English decoder (per ARCHITECTURE.md
# Amendment #1). The requested language is echoed back separately for tracking.
_WHISPER_LANG_MAP = {"en": "en", "pidgin": "en"}


def transcribe(audio_path: str, language: str = "en") -> dict:
    """Run whisper-cli on a 16kHz mono WAV file.

    Returns {"text": str, "language": str, "duration_ms": int, "raw_stderr": str}.
    Raises RuntimeError on any failure with a descriptive message.
    """
    lang_used = _WHISPER_LANG_MAP.get(language, "en")

    if not Path(WHISPER_BIN).exists():
        raise RuntimeError(
            f"whisper-cli binary not found at {WHISPER_BIN}. "
            "Build whisper.cpp or set FARMTWIN_WHISPER_BIN."
        )
    if not Path(WHISPER_MODEL).exists():
        raise RuntimeError(
            f"whisper model not found at {WHISPER_MODEL}. "
            "Download ggml-base-q5_1.bin or set FARMTWIN_WHISPER_MODEL."
        )
    if not Path(audio_path).exists():
        raise RuntimeError(f"audio file not found: {audio_path}")

    cmd = [
        WHISPER_BIN,
        "-m", WHISPER_MODEL,
        "-l", lang_used,
        "-f", audio_path,
        "-nt",  # no timestamps in stdout output
    ]

    t_start = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(
            f"whisper-cli timed out after 60s on {audio_path}"
        ) from e
    except FileNotFoundError as e:
        raise RuntimeError(f"whisper-cli invocation failed: {e}") from e
    duration_ms = int((time.time() - t_start) * 1000)

    if proc.returncode != 0:
        raise RuntimeError(
            f"whisper-cli exited with code {proc.returncode}: "
            f"{proc.stderr.strip()[:500]}"
        )

    text = proc.stdout.strip()
    if not text:
        # Very short/silent clips can produce empty stdout; log stderr snippet.
        raise RuntimeError(
            "whisper-cli produced no transcript "
            f"(stderr: {proc.stderr.strip()[:200]})"
        )

    return {
        "text": text,
        "language": lang_used,
        "duration_ms": duration_ms,
        "raw_stderr": proc.stderr[-500:] if proc.stderr else "",
    }
