"""FarmTwin backend entrypoint.

Run from inside the `backend/` directory:

    uvicorn app.main:app --reload --port 8000

This creates `farmtwin.db` next to the process CWD and serves the API on
http://127.0.0.1:8000. Health check: GET /api/health.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ask, crops, farms, fields, observations, transcribe, weather
from app.db import models  # noqa: F401  (ensure models are registered on Base)
from app.db.session import Base, engine

app = FastAPI(title="FarmTwin API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


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
