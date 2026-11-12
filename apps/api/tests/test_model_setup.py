import hashlib
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.ai import setup as model_setup
from app.ai.setup import ModelFile, Setup
from app.config import get_settings

BODY = bytes(range(256)) * 4096  # 1 MiB
SEEN_RANGES: list[str | None] = []


class Handler(BaseHTTPRequestHandler):
    """Serves BODY with Range support, like the model host."""

    def do_GET(self):
        SEEN_RANGES.append(self.headers.get("Range"))
        data = BODY if self.path == "/model.gguf" else b"not the model" * 1000
        start = 0
        if rng := self.headers.get("Range"):
            start = int(rng.split("=")[1].split("-")[0])
        self.send_response(206 if start else 200)
        self.send_header("Content-Length", str(len(data) - start))
        self.end_headers()
        self.wfile.write(data[start:])

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def host():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


@pytest.fixture()
def pinned(monkeypatch, tmp_path, host):
    def pin(path="/model.gguf", body=BODY):
        model = ModelFile(
            "Test model",
            "model.gguf",
            host + path,
            hashlib.sha256(body).hexdigest(),
            len(body),
            "model",
            "1 MB",
        )
        monkeypatch.setattr(model_setup, "LLM", model)
        monkeypatch.setattr(model_setup.setup, "model", model)  # the app's instance
        return model

    monkeypatch.setattr(get_settings(), "llm_model_path", tmp_path / "models" / "model.gguf")
    monkeypatch.setenv(
        "NO_PROXY", "127.0.0.1"
    )  # the real download honours system proxies; this host is local
    SEEN_RANGES.clear()
    return pin


def wait(s: Setup, *states, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if s.progress().state in states:
            return s.progress()
        time.sleep(0.05)
    raise AssertionError(f"stuck at {s.progress()}")


def test_download_checks_the_file_then_starts_the_model(pinned):
    pinned()
    started = []
    s = Setup(model_setup.LLM, model_setup.model_path)
    s.start_download(on_ready=lambda: started.append(True))
    wait(s, "ready")
    assert model_setup.model_path().read_bytes() == BODY
    assert started == [True]


def test_download_resumes_from_what_is_on_disk(pinned):
    pinned()
    part = model_setup.model_path().with_name("model.gguf.part")
    part.parent.mkdir(parents=True)
    part.write_bytes(BODY[:300_000])
    s = Setup(model_setup.LLM, model_setup.model_path)
    assert s.progress().state == "paused" and s.progress().done == 300_000
    s.start_download()
    wait(s, "ready")
    assert SEEN_RANGES == ["bytes=300000-"]
    assert model_setup.model_path().read_bytes() == BODY


def test_a_wrong_download_is_thrown_away(pinned):
    pinned(path="/other.gguf", body=BODY)  # serves different bytes than the pin expects
    s = Setup(model_setup.LLM, model_setup.model_path)
    s.start_download()
    p = wait(s, "error")
    assert "isn't the FarmTwin model" in p.error
    assert not model_setup.model_path().exists()
    assert not model_setup.model_path().with_name("model.gguf.part").exists()


def test_import_checks_before_copying(pinned, tmp_path):
    pinned()
    wrong = tmp_path / "wrong.gguf"
    wrong.write_bytes(b"x" * 1000)
    s = Setup(model_setup.LLM, model_setup.model_path)
    s.start_import(wrong)
    wait(s, "error")
    assert not model_setup.model_path().exists()

    right = tmp_path / "from-flash-drive.gguf"
    right.write_bytes(BODY)
    s.start_import(right)
    wait(s, "ready")
    assert model_setup.model_path().read_bytes() == BODY


def test_setup_endpoints(client, pinned, tmp_path):
    pinned()
    assert client.get("/api/model/setup").json()["state"] == "missing"
    missing = client.post("/api/model/setup/import", json={"path": str(tmp_path / "nope.gguf")})
    assert missing.json()["error"]["code"] == "file_not_found"
    source = tmp_path / "copy.gguf"
    source.write_bytes(BODY)
    assert client.post("/api/model/setup/import", json={"path": f'"{source}"'}).status_code == 202
    wait(model_setup.setup, "ready")
    assert client.get("/api/model/setup").json()["state"] == "ready"
