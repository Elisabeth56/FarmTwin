"""Starts, watches and restarts llama-server when the API is told where it is (ADR-027).

Without a configured binary the API uses whatever answers at `llama_url` and can only report on it.
"""

import logging
import socket
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Literal

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

State = Literal["ready", "starting", "stopped", "not_set_up"]
STARTUP_SECONDS = 120  # a 3B model can take a while to load on a slow disk


@dataclass
class Status:
    state: State
    managed: bool  # True when the API started llama-server and can restart it
    detail: str = ""


class Supervisor:
    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None
        self._url: str | None = None
        self._started_at = 0.0
        self._tail: deque[str] = deque(maxlen=20)
        self._lock = threading.Lock()

    @property
    def managed(self) -> bool:
        s = get_settings()
        return bool(s.llama_server_bin and s.llm_model_path)

    @property
    def url(self) -> str:
        return self._url or get_settings().llama_url.rstrip("/")

    def start(self) -> None:
        """Spawns llama-server on a free port. Does nothing if it isn't configured or is running."""
        with self._lock:
            if not self.managed or (self._proc and self._proc.poll() is None):
                return
            settings = get_settings()
            if not (settings.llm_model_path and settings.llm_model_path.exists()):
                logger.warning("model file missing: %s", settings.llm_model_path)
                return
            port = _free_port()
            self._tail.clear()
            self._proc = subprocess.Popen(
                command(port),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            self._url = f"http://127.0.0.1:{port}"
            self._started_at = time.monotonic()
            # keep the last lines of its log, so a crash can be explained
            threading.Thread(target=self._read_log, args=(self._proc,), daemon=True).start()
            logger.info("llama-server starting pid=%s port=%s", self._proc.pid, port)

    def stop(self) -> None:
        with self._lock:
            proc, self._proc = self._proc, None
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

    def restart(self) -> None:
        self.stop()
        self.start()

    def status(self) -> Status:
        if not self.managed:
            return Status("ready" if _healthy(self.url) else "stopped", managed=False)
        path = get_settings().llm_model_path
        if path is None or not path.exists():
            return Status("not_set_up", managed=True, detail="No model file yet.")
        proc = self._proc
        if proc is None or proc.poll() is not None:
            code = proc.returncode if proc else None
            return Status("stopped", managed=True, detail=_explain(code, list(self._tail)))
        if _healthy(self.url):
            return Status("ready", managed=True)
        if time.monotonic() - self._started_at < STARTUP_SECONDS:
            return Status("starting", managed=True)
        return Status("stopped", managed=True, detail="The model didn't finish loading.")

    def _read_log(self, proc: subprocess.Popen) -> None:
        assert proc.stderr is not None
        for line in proc.stderr:
            self._tail.append(line.rstrip())


def command(port: int) -> list[str]:
    s = get_settings()
    return [
        str(s.llama_server_bin),
        "--model", str(s.llm_model_path),
        "--host", "127.0.0.1",
        "--port", str(port),
        "--ctx-size", str(s.llm_context),
    ]  # fmt: skip


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _healthy(url: str) -> bool:
    try:
        # llama-server is always local: ignore any system proxy settings
        return httpx.get(f"{url}/health", timeout=2.0, trust_env=False).status_code == 200
    except httpx.HTTPError:
        return False


def _explain(code: int | None, tail: list[str]) -> str:
    """A plain reason for the stop. Memory is the usual cause on 8GB laptops."""
    text = "\n".join(tail).lower()
    if code in (-9, 137) or "out of memory" in text or "failed to allocate" in text:
        return "The system shut the model down, usually because the laptop ran low on memory. Close other apps, then restart it."
    if "failed to load model" in text:
        return "The model file couldn't be loaded. It may be damaged; import or download it again."
    return "The model stopped unexpectedly."


supervisor = Supervisor()
