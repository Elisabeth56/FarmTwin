"""FarmTwin backend entrypoint.

Run from inside the `apps/api/` directory (or `pnpm dev` from the repo root):

    uvicorn app.main:app --reload --port 8000

The database lives in the FarmTwin data folder (see app/config.py). Health check: GET /api/health.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ask, transcribe
from app.config import get_settings
from app.db import models  # noqa: F401  (ensure models are registered on Base)
from app.db.migrate import run_migrations
from app.errors import install_error_handlers
from app.features.farms import router as farms
from app.features.fields import router as fields
from app.features.observations import router as observations
from app.features.plantings import router as plantings
from app.features.weather import router as weather
from app.logs import install_request_logging, setup_logging


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    # the app only starts serving (and /api/health only answers) once the schema is current
    run_migrations()
    yield


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
app.include_router(ask.router)
app.include_router(transcribe.router)
