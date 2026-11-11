"""App settings: paths, ports and model names, validated once at startup.

Every value can be overridden with a FARMTWIN_* environment variable or a .env file.
Data lives in the OS app data folder so an installed app never writes next to its code.
"""

from functools import lru_cache
from pathlib import Path

from platformdirs import user_data_dir
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    llm_model: str = "qwen2.5-3b-instruct-q4_k_m"
    embedder_model: str = "all-MiniLM-L6-v2"
    whisper_model: str = "rishabbahal/whisper-small-nigerian-accent"
    # crop rule files and corpus; the desktop build points this at its bundled copy
    knowledge_dir: Path = Path(__file__).resolve().parents[3] / "knowledge"

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
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"


@lru_cache
def get_settings() -> Settings:
    return Settings()
