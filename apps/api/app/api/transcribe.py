"""/api/transcribe — accept an audio blob, return the transcribed text.

Pipeline: uploaded audio → ffmpeg to 16kHz mono WAV → whisper.cpp → text.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/transcribe", tags=["transcribe"])

MAX_AUDIO_BYTES = 5 * 1024 * 1024  # 5MB → ~30s at typical opus bitrates
VALID_LANGUAGES = {"en"}


@router.post("")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form("en"),
):
    """Transcribe an uploaded audio file.

    Accepts anything ffmpeg can read (webm, opus, wav, mp3, ...).
    Returns {text, language_requested, language_used, duration_ms}.
    """
    if language == "pidgin":
        raise HTTPException(
            status_code=400,
            detail="Nigerian Pidgin STT is not currently supported. Use English.",
        )
    if language not in VALID_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"language must be one of {sorted(VALID_LANGUAGES)}",
        )

    data = await audio.read()
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"audio too large ({len(data)} bytes); " f"limit is {MAX_AUDIO_BYTES} bytes (~30s recording)"
            ),
        )
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="empty audio upload")

    # Temp files for both raw upload and the 16kHz mono WAV.
    input_path: str | None = None
    wav_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".upload") as f_in:
            f_in.write(data)
            input_path = f_in.name

        wav_fd, wav_path = tempfile.mkstemp(suffix=".wav")
        os.close(wav_fd)

        # Convert to whisper-friendly format: 16kHz mono PCM s16le.
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            wav_path,
        ]
        try:
            proc = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            raise HTTPException(
                status_code=500,
                detail="ffmpeg timed out converting audio",
            ) from None
        except FileNotFoundError:
            raise HTTPException(
                status_code=500,
                detail="ffmpeg not installed on server",
            ) from None
        if proc.returncode != 0:
            logger.warning("ffmpeg failed: %s", proc.stderr[-500:])
            raise HTTPException(
                status_code=500,
                detail=("ffmpeg failed to decode audio: " f"{proc.stderr.strip()[-300:]}"),
            )

        try:
            from app.stt import whisper_client  # heavy; loaded on first use

            result = whisper_client.transcribe(wav_path, language=language)
        except RuntimeError as e:
            logger.warning("whisper transcription failed: %s", e)
            raise HTTPException(
                status_code=500,
                detail=f"transcription failed: {e}",
            ) from e

        return {
            "text": result["text"],
            "language_requested": language,
            "language_used": result["language"],
            "duration_ms": result["duration_ms"],
        }
    finally:
        for path in (input_path, wav_path):
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass
