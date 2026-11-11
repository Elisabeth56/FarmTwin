# ADR-015: FastAPI stays the backend, shipped as a Tauri sidecar

- Status: Accepted
- Date: 2026-11-11

## Context
The desktop app (ADR-022) needs a backend process. v1's logic is in Python, and the AI tooling (embeddings, ingestion, evals) is Python-first.

## Options
- **FastAPI sidecar.** Reuse v1 code; Tauri starts and stops it.
- **Move the logic into Rust inside Tauri.** One process and mobile-friendly, but a full rewrite in a language that isn't core to this project.
- **Node sidecar.** No advantage over Python for this workload.

## Decision
FastAPI, frozen with PyInstaller and started by Tauri as a sidecar. Code moves to feature folders (`features/<feature>/router.py, schemas.py, logic.py`) with one settings module and one error format.

## Consequences
- The desktop app runs three processes: Tauri shell, FastAPI, llama-server.
- Mobile cannot reuse the Python backend. ADR-019 keeps crop logic as data so a later port is a translation, not a redesign.
