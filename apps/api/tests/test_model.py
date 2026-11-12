import os
import signal
import sys
import time
from pathlib import Path

import pytest

from app.ai import server
from app.config import get_settings

FAKE = Path(__file__).resolve().parents[1] / "scripts" / "fake_llama.py"


def wait_for(state, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = server.supervisor.status()
        if status.state == state:
            return status
        time.sleep(0.2)
    raise AssertionError(f"never reached {state}; last {server.supervisor.status()}")


@pytest.fixture()
def managed(monkeypatch, tmp_path):
    model = tmp_path / "model.gguf"
    model.write_bytes(b"not a real model")
    settings = get_settings()
    monkeypatch.setattr(settings, "llama_server_bin", Path(sys.executable))
    monkeypatch.setattr(settings, "llm_model_path", model)
    monkeypatch.setattr(server, "command", lambda port: [sys.executable, str(FAKE), "--port", str(port)])
    yield server.supervisor
    server.supervisor.stop()


def test_supervised_model_starts_dies_and_restarts(client, managed):
    managed.start()
    assert wait_for("ready").managed
    assert client.get("/api/model/status").json()["state"] == "ready"

    os.kill(managed._proc.pid, signal.SIGKILL)  # what the OS does when memory runs out
    stopped = wait_for("stopped", timeout=5)
    assert "memory" in stopped.detail

    assert client.post("/api/model/restart").status_code == 200
    wait_for("ready")


def test_missing_model_file_means_not_set_up(client, monkeypatch, tmp_path):
    settings = get_settings()
    monkeypatch.setattr(settings, "llama_server_bin", Path(sys.executable))
    monkeypatch.setattr(settings, "llm_model_path", tmp_path / "nothing.gguf")
    assert client.get("/api/model/status").json()["state"] == "not_set_up"


def test_unmanaged_model_cannot_be_restarted_from_the_app(client):
    body = client.post("/api/model/restart").json()
    assert body["error"]["code"] == "model_not_managed"
    assert client.get("/api/model/status").json()["managed"] is False


def test_shutdown_needs_the_shell_token(client, monkeypatch):
    from app.features.system import router as system

    stopped = []
    monkeypatch.setattr(system, "_exit", lambda reason: stopped.append(reason))
    assert client.post("/api/shutdown").status_code == 403  # no token configured
    monkeypatch.setattr(get_settings(), "shutdown_token", "s3cret")
    assert client.post("/api/shutdown", headers={"X-FarmTwin-Token": "wrong"}).status_code == 403
    assert client.post("/api/shutdown", headers={"X-FarmTwin-Token": "s3cret"}).status_code == 202
    time.sleep(0.1)
    assert stopped == ["shell asked"]
