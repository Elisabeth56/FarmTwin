"""Speech to text with whisper.cpp (ADR-017). The browser sends 16 kHz mono 16-bit WAV, so there
is no audio conversion here; whisper-cli runs once per recording and exits, so the voice model
is only in memory while it transcribes."""

import io
import logging
import os
import subprocess
import tempfile
import time
import wave

from app.ai.setup import voice_model_path
from app.config import get_settings
from app.errors import AppError

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16_000
MAX_SECONDS = 30
TIMEOUT_S = 90


def cli_present() -> bool:
    cli = get_settings().whisper_cli_bin
    return cli is not None and cli.exists()


def unavailable_reason() -> str | None:
    """Why voice input is off, in words for the user, or None when it's ready."""
    if not cli_present():
        return "Voice input isn't part of this build. Type your question instead."
    if not voice_model_path().exists():
        return "Voice input needs the voice model, about 190 MB, once."
    return None


def check_wav(data: bytes) -> float:
    """Returns the recording's length in seconds; rejects anything but 16 kHz mono 16-bit WAV."""
    try:
        with wave.open(io.BytesIO(data)) as w:
            ok = (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (SAMPLE_RATE, 1, 2)
            seconds = w.getnframes() / SAMPLE_RATE
    except (wave.Error, EOFError):
        ok, seconds = False, 0.0
    if not ok:
        raise AppError(400, "bad_audio", "The recording couldn't be read. Try again.")
    if seconds < 0.3:
        raise AppError(400, "empty_audio", "The recording was too short. Hold the mic a little longer.")
    if seconds > MAX_SECONDS + 1:
        raise AppError(413, "audio_too_long", f"Recordings can be up to {MAX_SECONDS} seconds.")
    return seconds


def transcribe(data: bytes) -> tuple[str, int]:
    """Returns the text and how long transcription took in milliseconds."""
    if reason := unavailable_reason():
        raise AppError(409, "voice_unavailable", reason)
    check_wav(data)

    s = get_settings()
    fd, path = tempfile.mkstemp(suffix=".wav")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        cmd = [
            str(s.whisper_cli_bin),
            *("-m", str(voice_model_path())),
            *("-f", path),
            *("-l", "en"),
            *("-t", str(max(1, min(4, (os.cpu_count() or 2) - 1)))),
            "-nt",  # no timestamps
            "-np",  # only the transcript on stdout
        ]
        started = time.monotonic()
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_S, check=False)
        except subprocess.TimeoutExpired:
            raise AppError(
                504, "transcription_timeout", "Transcribing took too long. Try a shorter recording."
            ) from None
        if proc.returncode != 0:
            logger.warning("whisper-cli failed (%s): %s", proc.returncode, proc.stderr[-500:])
            raise AppError(500, "transcription_failed", "The recording couldn't be transcribed. Try again.")
        elapsed = int((time.monotonic() - started) * 1000)
    finally:
        os.unlink(path)

    # whisper marks silence and noise as [BLANK_AUDIO], (wind) and similar
    text = " ".join(line.strip() for line in proc.stdout.splitlines() if line.strip())
    if not text or text.startswith("[") and text.endswith("]"):
        raise AppError(422, "nothing_heard", "Nothing was heard. Check the mic and try again.")
    return text, elapsed
