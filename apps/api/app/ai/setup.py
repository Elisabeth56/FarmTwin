"""Getting the model onto the laptop (ADR-023): a resumable download or an import from a file,
both checked against the pinned SHA-256 before the file is used."""

import hashlib
import logging
import shutil
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelFile:
    name: str
    filename: str
    url: str
    sha256: str
    size: int


# pinned per release; a different model means a new FarmTwin version
LLM = ModelFile(
    name="Qwen2.5-3B Instruct (Q4_K_M)",
    filename="qwen2.5-3b-instruct-q4_k_m.gguf",
    url="https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
    sha256="626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d",
    size=2_104_932_768,
)

State = Literal["missing", "downloading", "paused", "verifying", "ready", "error"]
CHUNK = 1 << 20


def model_path() -> Path:
    """Where the model lives: the configured path, or the app's models folder."""
    s = get_settings()
    return s.llm_model_path or s.models_dir / LLM.filename


@dataclass
class Progress:
    state: State = "missing"
    done: int = 0
    total: int = field(default_factory=lambda: LLM.size)
    error: str = ""
    # set while running; cleared when the work stops
    _stop: threading.Event = field(default_factory=threading.Event, repr=False)


class Setup:
    """One download or import at a time; the app polls `progress()`."""

    def __init__(self) -> None:
        self._p = Progress()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def progress(self) -> Progress:
        busy = self._thread is not None and self._thread.is_alive()
        if not busy and self._p.state not in ("error", "paused"):
            if model_path().exists():
                self._p.state, self._p.done = "ready", LLM.size
            else:
                part = _part(model_path())
                self._p.state = "paused" if part.exists() else "missing"
                self._p.done = part.stat().st_size if part.exists() else 0
        return self._p

    def start_download(self, on_ready=None) -> None:
        self._run(self._download, on_ready)

    def start_import(self, source: Path, on_ready=None) -> None:
        if not source.is_file():
            raise FileNotFoundError(source)
        self._run(lambda: self._import(source), on_ready)

    def pause(self) -> None:
        self._p._stop.set()

    def _run(self, work, on_ready) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._p = Progress(state="downloading")

            def target():
                try:
                    work()
                    if self._p.state == "ready" and on_ready:
                        on_ready()
                except Exception as exc:  # shown to the user as a plain message
                    logger.exception("model setup failed")
                    self._p.state, self._p.error = "error", _plain(exc)

            self._thread = threading.Thread(target=target, daemon=True)
            self._thread.start()

    def _download(self) -> None:
        dest = model_path()
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = _part(dest)
        have = part.stat().st_size if part.exists() else 0
        self._p.done = have
        # resume from what's already on disk; the server answers 206 with the rest
        headers = {"Range": f"bytes={have}-"} if have else {}
        with httpx.stream(
            "GET", LLM.url, headers=headers, follow_redirects=True, timeout=httpx.Timeout(30, read=120)
        ) as res:
            if res.status_code == 416:  # nothing left to fetch
                pass
            else:
                res.raise_for_status()
                if have and res.status_code != 206:  # server ignored the range: start over
                    have, self._p.done = 0, 0
                with part.open("ab" if have else "wb") as out:
                    for chunk in res.iter_bytes(CHUNK):
                        if self._p._stop.is_set():
                            self._p.state = "paused"
                            return
                        out.write(chunk)
                        self._p.done += len(chunk)
        self._verify_and_place(part, dest)

    def _import(self, source: Path) -> None:
        dest = model_path()
        dest.parent.mkdir(parents=True, exist_ok=True)
        # check the original first, so a wrong file is never copied
        self._verify(source)
        tmp = _part(dest)
        shutil.copyfile(source, tmp)
        tmp.replace(dest)
        self._p.state, self._p.done = "ready", LLM.size

    def _verify_and_place(self, part: Path, dest: Path) -> None:
        try:
            self._verify(part)
        except ValueError:
            part.unlink(missing_ok=True)  # a bad download can't be resumed into a good one
            raise
        part.replace(dest)
        self._p.state, self._p.done = "ready", LLM.size

    def _verify(self, path: Path) -> None:
        self._p.state, self._p.done, self._p.total = "verifying", 0, path.stat().st_size
        digest = hashlib.sha256()
        with path.open("rb") as f:
            while chunk := f.read(CHUNK):
                digest.update(chunk)
                self._p.done += len(chunk)
        if digest.hexdigest() != LLM.sha256:
            raise ValueError("model_mismatch")
        self._p.total = LLM.size


def _part(dest: Path) -> Path:
    return dest.with_name(dest.name + ".part")


def _plain(exc: Exception) -> str:
    if isinstance(exc, ValueError) and str(exc) == "model_mismatch":
        return "This file isn't the FarmTwin model, or it's damaged. Copy it again or download it fresh."
    if isinstance(exc, httpx.HTTPError):
        return "The download stopped. Check the connection and press Resume; it carries on where it left off."
    if isinstance(exc, OSError) and "No space" in str(exc):
        return "There isn't enough free space. The model needs about 2.5 GB."
    return "Something went wrong setting up the model. Try again."


setup = Setup()
