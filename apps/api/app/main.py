"""FarmTwin backend entrypoint.

Run from inside the `apps/api/` directory (or `pnpm dev` from the repo root):

    uvicorn app.main:app --reload --port 8000

The database lives in the FarmTwin data folder (see app/config.py). Health check: GET /api/health.
"""

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai.server import supervisor
from app.api import transcribe
from app.config import get_settings
from app.db import models  # noqa: F401  (ensure models are registered on Base)
from app.db.migrate import run_migrations
from app.errors import AppError, install_error_handlers
from app.features.ask import router as ask
from app.features.farms import router as farms
from app.features.fields import router as fields
from app.features.model import router as model
from app.features.observations import router as observations
from app.features.plantings import router as plantings
from app.features.system import router as system
from app.features.weather import router as weather
from app.logs import install_request_logging, setup_logging
from app.rag.index import sync_index


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    # the app only starts serving (and /api/health only answers) once the schema is current
    run_migrations()
    # keep the search index in step with the shipped guides; in the background so the app
    # opens at once (questions asked in the first seconds wait for nothing, they just find less)
    threading.Thread(target=_sync_index_quietly, daemon=True).start()
    supervisor.start()
    system.watch_parent()
    yield
    supervisor.stop()


def _sync_index_quietly() -> None:
    try:
        sync_index()
    except AppError as exc:  # e.g. the embedder files are missing; retrieval will say so
        logging.getLogger(__name__).warning("index not synced: %s", exc.message)
    except Exception:
        logging.getLogger(__name__).exception("index sync failed")


app = FastAPI(title="FarmTwin API", version="0.2.0", lifespan=lifespan)
install_error_handlers(app)
install_request_logging(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(farms.router)
app.include_router(fields.router)
app.include_router(plantings.router)
app.include_router(observations.router)
app.include_router(weather.router)
app.include_router(model.router)
app.include_router(system.router)
app.include_router(ask.router)
app.include_router(transcribe.router)
