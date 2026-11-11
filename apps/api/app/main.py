"""FarmTwin backend entrypoint.

Run from inside the `apps/api/` directory (or `pnpm dev` from the repo root):

    uvicorn app.main:app --reload --port 8000

The database lives in the FarmTwin data folder (see app/config.py). Health check: GET /api/health.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ask, crops, farms, fields, observations, transcribe, weather
from app.config import get_settings
from app.db import models  # noqa: F401  (ensure models are registered on Base)
from app.db.session import Base, engine
from app.errors import install_error_handlers
from app.logs import install_request_logging, setup_logging


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    Base.metadata.create_all(bind=engine)
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
app.include_router(crops.router)
app.include_router(observations.router)
app.include_router(weather.router)
app.include_router(ask.router)
app.include_router(transcribe.router)
