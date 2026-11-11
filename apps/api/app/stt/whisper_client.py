"""HuggingFace Whisper client — Nigerian-accented English fine-tune.

Loads the configured Whisper model once, on first import, and reuses it for every request.
Imported lazily by the transcribe endpoint so the API starts without the voice extras.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor

from app.config import get_settings

logger = logging.getLogger(__name__)


MODEL_ID = get_settings().whisper_model
SAMPLE_RATE = 16000

logger.info("loading whisper model %s", MODEL_ID)
_processor = WhisperProcessor.from_pretrained(MODEL_ID)
_model = WhisperForConditionalGeneration.from_pretrained(MODEL_ID)
_model.eval()
_param_count_m = sum(p.numel() for p in _model.parameters()) / 1_000_000
logger.info("whisper ready (%.1fM params)", _param_count_m)


def transcribe(audio_path: str, language: str = "en") -> dict:
    """Transcribe a 16kHz mono WAV file with the Nigerian-accented fine-tune.

    Returns {"text": str, "language": str, "duration_ms": int, "raw_stderr": str}.
    Raises RuntimeError on any failure.
    """
    if language != "en":
        logger.warning("whisper_hf: language=%r ignored; this model is English-only", language)

    if not Path(audio_path).exists():
        raise RuntimeError(f"audio file not found: {audio_path}")

    t_start = time.time()
    try:
        audio, sr = sf.read(audio_path)
    except FileNotFoundError as e:
        raise RuntimeError(f"audio file not found: {audio_path}") from e
    except Exception as e:
        raise RuntimeError(f"failed to read audio {audio_path}: {e}") from e

    if sr != SAMPLE_RATE:
        raise RuntimeError(f"expected {SAMPLE_RATE}Hz audio, got {sr}Hz " "(upstream ffmpeg should resample)")

    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    audio = audio.astype(np.float32)

    try:
        inputs = _processor(audio, sampling_rate=SAMPLE_RATE, return_tensors="pt")
        with torch.no_grad():
            predicted_ids = _model.generate(
                inputs.input_features,
                max_new_tokens=200,
                language="en",
                task="transcribe",
            )
        text = _processor.batch_decode(predicted_ids, skip_special_tokens=True)[0].strip()
    except Exception as e:
        raise RuntimeError(f"whisper HF inference failed: {e}") from e

    duration_ms = int((time.time() - t_start) * 1000)

    if not text:
        raise RuntimeError("whisper HF produced empty transcript")

    return {
        "text": text,
        "language": "en",
        "duration_ms": duration_ms,
        "raw_stderr": "",
    }
