# ADR-023: Model delivery by download or file import

- Status: Accepted
- Date: 2026-11-11

## Context
The LLM file is about 2GB, too large for the installer. Getting the app needs internet once, but many officers receive software from someone who already has it (flash drive, laptop-to-laptop copy at a training). A download-only flow fails on a laptop that got the installer offline.

## Options
- **Download on first launch only.**
- **Download, with "Import model file" as an alternative.**
- **Bundle the model in the installer.** Simple, but a 2GB+ installer per OS.

## Decision
The first-run screen offers both: download (resumable, with progress) or import a `.gguf` from disk. Both paths verify the file against a pinned SHA-256 before use. Models live in the OS app data folder, outside the app, so app updates never re-download them. Voice models (ADR-017) use the same flow.

## Consequences
- One officer can download once and share the file with every laptop at a training.
- The pinned checksum list ships with each release; a new model means a new release.
- The update check fails quietly when offline.
