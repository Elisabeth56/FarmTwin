# ADR-010: whisper.cpp pinned tag
Date: 2026-08-22
Status: Accepted
Context: Need reproducible STT for Day 7 submission.
Decision: whisper.cpp tag v1.9.3, built CPU-only with GGML_METAL=OFF, GGML_ACCELERATE=OFF, WHISPER_COREML=OFF. Located at ~/dev/tools/whisper.cpp/.
Consequences: setup.sh on Day 7 must clone + checkout this tag + build with same flags.
