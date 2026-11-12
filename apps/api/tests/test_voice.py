import io
import sys
import wave

import pytest

from app.config import get_settings

FAKE_CLI = """#!{python}
import sys
args = sys.argv[1:]
model, wav = args[args.index("-m") + 1], args[args.index("-f") + 1]
said = open(model).read().strip()
if said == "crash":
    sys.exit(3)
print(said)
"""


def wav(seconds: float, rate: int = 16_000, channels: int = 1) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\0\0" * int(seconds * rate) * channels)
    return buf.getvalue()


@pytest.fixture()
def voice(monkeypatch, tmp_path):
    """A stand-in whisper-cli that prints whatever the 'model file' says."""
    cli = tmp_path / "whisper-cli"
    cli.write_text(FAKE_CLI.format(python=sys.executable))
    cli.chmod(0o755)
    model = tmp_path / "voice.bin"
    monkeypatch.setattr(get_settings(), "whisper_cli_bin", cli)
    monkeypatch.setattr(get_settings(), "voice_model_path", model)

    def say(text: str):
        model.write_text(text)

    return say


def post(client, data: bytes):
    return client.post("/api/voice/transcribe", files={"audio": ("rec.wav", data, "audio/wav")})


def test_voice_is_off_without_the_cli(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "whisper_cli_bin", None)
    status = client.get("/api/voice/status").json()
    assert status["ready"] is False and "isn't part of this build" in status["reason"]
    assert status["needs_model"] is False
    assert post(client, wav(1)).json()["error"]["code"] == "voice_unavailable"


def test_voice_is_off_until_the_voice_model_is_set_up(client, voice):
    status = client.get("/api/voice/status").json()
    assert status["ready"] is False and status["needs_model"] is True


def test_a_recording_comes_back_as_text(client, voice):
    voice("My maize leaves are turning yellow.")
    assert client.get("/api/voice/status").json()["ready"] is True
    res = post(client, wav(2))
    assert res.status_code == 200
    assert res.json()["text"] == "My maize leaves are turning yellow."


@pytest.mark.parametrize(
    "audio,code",
    [
        (wav(1, rate=44_100), "bad_audio"),
        (wav(1, channels=2), "bad_audio"),
        (b"not audio", "bad_audio"),
        (wav(0.1), "empty_audio"),
        (wav(40), "audio_too_long"),
    ],
)
def test_only_short_16k_mono_wav_is_accepted(client, voice, audio, code):
    voice("hello")
    assert post(client, audio).json()["error"]["code"] == code


def test_silence_and_crashes_get_plain_messages(client, voice):
    voice("[BLANK_AUDIO]")
    assert post(client, wav(1)).json()["error"]["code"] == "nothing_heard"
    voice("crash")
    assert post(client, wav(1)).json()["error"]["code"] == "transcription_failed"
