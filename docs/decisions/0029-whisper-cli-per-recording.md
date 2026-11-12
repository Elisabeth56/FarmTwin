# ADR-029: whisper-cli runs once per recording; the stock small.en model ships first

- Status: Accepted
- Date: 2026-11-12
- Amends: ADR-017 (how whisper.cpp runs, which voice model)

## Context
ADR-017 puts whisper.cpp in a sidecar and plans a Nigerian-accent Whisper fine-tune converted to GGML. Two things changed while building it (#16):

- AGENTS.md §4 asks for whisper.cpp to be loaded only while transcribing. A whisper-server kept running holds its model in memory next to the language model the whole time.
- Converting the fine-tune and re-running WER on the converted file needs the source model and a WER harness run, and neither has happened yet.

## Options
- **whisper-server, supervised like llama-server.** Fast repeat requests; the model stays in memory.
- **whisper-cli, one process per recording.** Loads the model per request (a short delay), frees all of it when done; no supervision code.

For the model:
- **The stock English model** `ggml-small.en-q5_1.bin` from whisper.cpp's model repo, pinned by SHA-256 (190 MB).
- **Wait for the converted fine-tune.**

## Decision
whisper-cli runs once per recording, built from whisper.cpp source at a pinned tag in the installer build (whisper.cpp has no prebuilt Mac or Linux binaries). The browser sends 16 kHz mono 16-bit WAV, so there is no ffmpeg. Voice ships with the stock `small.en` Q5_1 model as an optional download or import (ADR-023 flow). The fine-tune can replace it once it's converted and measured.

## Consequences
- Voice uses no memory until the mic is pressed; each recording pays the model load time. Neither the load time, the peak memory nor the WER on Nigerian-accented speech has been measured yet; they go in `docs/v1/benchmarks.md` after a real run.
- Recordings are capped at 30 seconds (the app stops at 15).
- x86 builds of whisper-cli need AVX2.
- The PyTorch voice path and the `ml` extra are removed.
