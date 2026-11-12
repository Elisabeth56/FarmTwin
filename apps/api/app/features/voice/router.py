"""Voice input: whether it's ready, getting the voice model, and transcribing a recording."""

from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.ai.setup import voice_setup
from app.errors import AppError
from app.features.model.router import ImportIn, SetupOut
from app.features.voice import whisper

router = APIRouter(prefix="/api/voice", tags=["voice"])

MAX_UPLOAD = 2 * 1024 * 1024  # 30 s of 16 kHz 16-bit mono is ~1 MB


class VoiceStatus(BaseModel):
    ready: bool
    reason: str | None
    # true when only the voice model is missing, so the app can offer to get it
    needs_model: bool


class TranscriptOut(BaseModel):
    text: str
    took_ms: int


@router.get("/status", response_model=VoiceStatus)
def voice_status():
    reason = whisper.unavailable_reason()
    needs_model = reason is not None and whisper.cli_present()
    return VoiceStatus(ready=reason is None, reason=reason, needs_model=needs_model)


@router.post("/transcribe", response_model=TranscriptOut)
async def transcribe(audio: UploadFile = File(...)):
    data = await audio.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise AppError(413, "audio_too_long", f"Recordings can be up to {whisper.MAX_SECONDS} seconds.")
    text, took = await run_in_threadpool(whisper.transcribe, data)
    return TranscriptOut(text=text, took_ms=took)


@router.get("/setup", response_model=SetupOut)
def setup_progress():
    p = voice_setup.progress()
    m = voice_setup.model
    return SetupOut(state=p.state, done=p.done, total=p.total, error=p.error, model_name=m.name, size=m.size)


@router.post("/setup/download", response_model=SetupOut, status_code=202)
def start_download():
    voice_setup.start_download()
    return setup_progress()


@router.post("/setup/pause", response_model=SetupOut)
def pause_download():
    voice_setup.pause()
    return setup_progress()


@router.post("/setup/import", response_model=SetupOut, status_code=202)
def import_model(body: ImportIn):
    source = Path(body.path.strip().strip('"')).expanduser()
    if not source.is_file():
        raise AppError(404, "file_not_found", "There's no file at that path. Pick the .bin file again.")
    voice_setup.start_import(source)
    return setup_progress()
