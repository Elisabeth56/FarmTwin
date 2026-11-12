# ADR-017: Speech-to-text with whisper.cpp; voice models as an optional pack

- Status: Accepted
- Date: 2026-11-11

## Context
v1 STT ran a Hugging Face Whisper fine-tune through transformers and PyTorch (not listed in requirements.txt), downloaded on first load, and used ffmpeg for audio conversion. None of that packages well or works offline on a fresh machine.

## Options
- **transformers + PyTorch.** Current; heavy and online-dependent.
- **whisper.cpp sidecar.** Same family as llama.cpp, CPU-friendly, GGML model files.
- **sherpa-onnx.** Light and capable, but a different model format from the rest of the stack.

## Decision
whisper.cpp runs as a sidecar. Whisper-based fine-tunes are converted to GGML. The browser records audio and encodes 16kHz mono WAV itself, so ffmpeg is not shipped. Voice models are an optional download or import, using the same flow as the LLM (ADR-023), so the base install stays smaller.

## Consequences
- Each candidate model needs a conversion step and a WER re-run on the converted file, since quantisation can change accuracy.
- Non-Whisper models (e.g. NeMo-based SBPN) are out unless a whisper.cpp-compatible path appears.
