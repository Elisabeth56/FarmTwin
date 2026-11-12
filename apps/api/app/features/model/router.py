"""The local model's state, for the sidebar card and the "model stopped" screen."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.ai.server import supervisor
from app.errors import AppError

router = APIRouter(prefix="/api/model", tags=["model"])


class ModelStatus(BaseModel):
    state: str
    managed: bool
    detail: str


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
