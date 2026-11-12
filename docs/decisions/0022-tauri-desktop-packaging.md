# ADR-022: Tauri v2 desktop app with FastAPI and llama-server sidecars

- Status: Accepted
- Date: 2026-11-11

## Context
FarmTwin should install like any other app on Windows, Linux, Intel Mac and Apple Silicon Mac, with no Python or build tools on the user's machine. The target laptop has 8GB RAM and also runs a 3B model.

## Options
- **Tauri v2.** Uses the OS web view; small shell and low memory.
- **Electron.** Bundles Chromium; more memory and a larger installer.
- **No shell.** A frozen backend that opens the browser at localhost; simplest, but no installer feel and no updater.

Sidecar packaging:
- **PyInstaller `--onefile`.** One binary, but it unpacks to a temp folder on every launch, which is slow on the 2014 Mac.
- **PyInstaller `--onedir`.** A folder; fast start.

## Decision
Tauri v2. FastAPI frozen with PyInstaller `--onedir`; llama-server and whisper-server use official prebuilt binaries per OS. On launch the backend binds a free localhost port and prints it; Tauri reads it, passes it to the UI, waits for `/api/health`, and kills all sidecars on exit.

Builds run on GitHub Actions for four targets: Windows x64, Linux x64, macOS x64, macOS arm64. Releases publish to GitHub Releases.

No paid code signing. macOS builds get free ad-hoc signatures (required on Apple Silicon). The README documents the Gatekeeper "Open Anyway" and SmartScreen "Run anyway" steps. Auto-update uses the Tauri updater with its own free signing keypair, separate from OS code signing.

## Consequences
- Users see an unknown-developer warning on first install on Mac and Windows.
- The NSIS installer can skip replacing a sidecar on reinstall (tauri-apps/tauri#15134); the installer hook stops running sidecars and deletes old binaries first.
- Rendering differs slightly across WebView2, WKWebView and WebKitGTK; the UI is checked on all three in CI screenshots.
