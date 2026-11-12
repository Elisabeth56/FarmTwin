"""App settings: paths, ports and model names, validated once at startup.

Every value can be overridden with a FARMTWIN_* environment variable or a .env file.
Data lives in the OS app data folder so an installed app never writes next to its code.
"""

import sys
from functools import lru_cache
from pathlib import Path

from platformdirs import user_data_dir
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _bundle_root() -> Path:
    """The repo root in development; the unpacked bundle when frozen by PyInstaller."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # pyright: ignore[reportAttributeAccessIssue]
    return Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FARMTWIN_", env_file=".env", extra="ignore")

    data_dir: Path = Field(default_factory=lambda: Path(user_data_dir("FarmTwin", appauthor=False)))
    host: str = "127.0.0.1"
    # 0 picks a free port; the chosen port is printed for the desktop shell to read
    port: int = 8000
    cors_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "tauri://localhost",
        "http://tauri.localhost",
    ]

    llama_url: str = "http://127.0.0.1:8080"
    # set to have the API start and supervise llama-server (ADR-027); leave unset to use a
    # llama-server you started yourself at llama_url
    llama_server_bin: Path | None = None
    # defaults to the pinned model file in models_dir (app/ai/setup.py)
    llm_model_path: Path | None = None
    # tests turn this off: each test client would start its own background index sync
    sync_index_on_start: bool = True
    llm_context: int = 4096
    llm_model: str = "qwen2.5-3b-instruct-q4_k_m"
    embedder_model: str = "BAAI/bge-small-en-v1.5"
    # fastembed model cache; the desktop build points this at the copy inside the installer
    embedder_dir: Path | None = None
    whisper_model: str = "rishabbahal/whisper-small-nigerian-accent"
    # vector distance (L2 between normalized embeddings) above which the closest chunk counts as "not in my sources"; tuned on
    # the eval set (evals/results/baseline-retrieval.json), re-check it after corpus or embedder changes
    retrieval_max_distance: float = 0.78
    # crop rule files and corpus; the desktop build points this at its bundled copy
    knowledge_dir: Path = Field(default_factory=lambda: _bundle_root() / "knowledge")
    # set by the desktop shell: the API exits when this process is gone, and only callers that
    # know the token may ask it to shut down
    parent_pid: int | None = None
    shutdown_token: str | None = None

    @field_validator("data_dir")
    @classmethod
    def data_dir_must_be_writable(cls, path: Path) -> Path:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".write-test"
            probe.touch()
            probe.unlink()
        except OSError as exc:
            raise ValueError(f"FarmTwin can't write to its data folder {path}: {exc}") from exc
        return path

    @property
    def database_path(self) -> Path:
        return self.data_dir / "farmtwin.db"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path}"

    @property
    def models_dir(self) -> Path:
        return self.data_dir / "models"

    @property
    def embedder_path(self) -> Path:
        return self.embedder_dir or self.models_dir / "embedder"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"


@lru_cache
def get_settings() -> Settings:
    return Settings()
