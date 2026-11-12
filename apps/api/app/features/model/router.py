"""The local model: its state for the sidebar and "model stopped" screen, and first-run setup."""

from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.ai.server import supervisor
from app.ai.setup import LLM, setup
from app.errors import AppError

router = APIRouter(prefix="/api/model", tags=["model"])


class ModelStatus(BaseModel):
    state: str
    managed: bool
    detail: str


class SetupOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    state: str
    done: int
    total: int
    error: str
    model_name: str
    size: int


class ImportIn(BaseModel):
    path: str


@router.get("/status", response_model=ModelStatus)
def model_status():
    s = supervisor.status()
    return ModelStatus(state=s.state, managed=s.managed, detail=s.detail)


@router.post("/restart", response_model=ModelStatus)
def restart_model():
    if not supervisor.managed:
        raise AppError(
            409,
            "model_not_managed",
            "FarmTwin didn't start the model here, so it can't restart it. Restart llama-server yourself.",
        )
    supervisor.restart()
    return model_status()


@router.get("/setup", response_model=SetupOut)
def setup_progress():
    p = setup.progress()
    return SetupOut(
        state=p.state, done=p.done, total=p.total, error=p.error, model_name=LLM.name, size=LLM.size
    )


@router.post("/setup/download", response_model=SetupOut, status_code=202)
def start_download():
    """Starts or resumes the download. The model starts once the file checks out."""
    setup.start_download(on_ready=supervisor.start)
    return setup_progress()


@router.post("/setup/pause", response_model=SetupOut)
def pause_download():
    setup.pause()
    return setup_progress()


@router.post("/setup/import", response_model=SetupOut, status_code=202)
def import_model(body: ImportIn):
    source = Path(body.path.strip().strip('"')).expanduser()
    if not source.is_file():
        raise AppError(404, "file_not_found", "There's no file at that path. Pick the .gguf file again.")
    setup.start_import(source, on_ready=supervisor.start)
    return setup_progress()
