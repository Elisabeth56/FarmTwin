"""Smoke test for the whisper.cpp STT pipeline.

Runs two checks:

    1. Direct: import backend.app.stt.whisper_client and transcribe jfk.wav.
    2. HTTP:  POST the same file to http://127.0.0.1:8000/api/transcribe
              (skipped if the backend isn't running).

Success criterion: the transcript contains the word "country".
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_WAV = Path.home() / "dev/tools/whisper.cpp/samples/jfk.wav"
BACKEND_URL = os.environ.get("FARMTWIN_BACKEND_URL", "http://127.0.0.1:8000")


def _add_backend_to_path() -> None:
    sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))


def test_direct() -> bool:
    print("=" * 60)
    print("Test 1: direct whisper_client.transcribe()")
    print("=" * 60)

    _add_backend_to_path()
    from app.stt.whisper_client import transcribe

    if not SAMPLE_WAV.exists():
        print(f"FAIL: sample file missing at {SAMPLE_WAV}")
        return False

    try:
        result = transcribe(str(SAMPLE_WAV), language="en")
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: transcribe raised {type(e).__name__}: {e}")
        return False

    text = result["text"]
    dur = result["duration_ms"]
    print(f"transcript: {text!r}")
    print(f"duration_ms: {dur}")

    if "country" in text.lower():
        print(f"PASS (contains 'country', took {dur} ms)")
        return True
    print("FAIL: transcript did not contain 'country'")
    return False


def test_http() -> bool:
    print()
    print("=" * 60)
    print("Test 2: POST /api/transcribe")
    print("=" * 60)

    try:
        import httpx
    except ImportError:
        print("SKIP: httpx not installed")
        return True

    if not SAMPLE_WAV.exists():
        print(f"FAIL: sample file missing at {SAMPLE_WAV}")
        return False

    url = f"{BACKEND_URL}/api/transcribe"
    try:
        with open(SAMPLE_WAV, "rb") as f:
            r = httpx.post(
                url,
                files={"audio": ("jfk.wav", f, "audio/wav")},
                data={"language": "en"},
                timeout=90,
            )
    except httpx.ConnectError:
        print(f"SKIP: backend not reachable at {BACKEND_URL}")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: request raised {type(e).__name__}: {e}")
        return False

    print(f"status: {r.status_code}")
    try:
        payload = r.json()
    except Exception:  # noqa: BLE001
        print(f"FAIL: response not JSON — body: {r.text[:200]}")
        return False
    print(f"body: {payload}")

    if r.status_code != 200:
        print(f"FAIL: expected 200, got {r.status_code}")
        return False
    text = str(payload.get("text", ""))
    if "country" in text.lower():
        print("PASS (endpoint returned transcript containing 'country')")
        return True
    print("FAIL: transcript did not contain 'country'")
    return False


def main() -> int:
    ok_direct = test_direct()
    ok_http = test_http()
    print()
    print(f"Direct test: {'PASS' if ok_direct else 'FAIL'}")
    print(f"HTTP test:   {'PASS' if ok_http else 'FAIL'}")
    return 0 if (ok_direct and ok_http) else 1


if __name__ == "__main__":
    sys.exit(main())
