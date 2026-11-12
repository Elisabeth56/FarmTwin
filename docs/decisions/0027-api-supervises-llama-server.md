# ADR-027: The API starts and restarts llama-server

- Status: Accepted
- Date: 2026-11-12
- Amends: ADR-022 (who owns the llama-server sidecar)

## Context
The "model stopped" screen (#23) needs a Restart button that works without restarting the app, and the sidebar needs to know the model's state. ADR-022 has Tauri spawn every sidecar. Then a restart from the UI would need a Tauri command, the status would live in Rust, and none of it would work in `pnpm dev` or be testable with pytest.

## Options
- **Tauri owns llama-server** (ADR-022 as written). Restart and status go through Tauri IPC; dev mode has no restart.
- **The API owns llama-server.** The API spawns it as a child process, watches it, and exposes `GET /api/model/status` and `POST /api/model/restart`. Tauri only spawns the API.

## Decision
The API owns llama-server. Tauri still spawns the API and kills it on exit; the API stops llama-server when it shuts down. If no llama-server binary is configured (`pnpm dev` with a llama-server you started yourself), the API only checks `llama_url`, and the UI says to restart it by hand.

## Consequences
- Status and restart work the same in dev and in the desktop app, and they're covered by pytest.
- One process tree: if the API dies, Tauri restarts it and it restarts llama-server.
- The API picks llama-server's port, so `llama_url` is set at runtime when it supervises the server.
- The desktop build (#25) passes the paths of the llama-server binary and the model to the API instead of spawning llama-server itself.
