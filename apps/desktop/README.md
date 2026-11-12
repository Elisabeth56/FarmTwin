# FarmTwin desktop

Tauri v2 shell (ADR-022, ADR-027). It starts the bundled API, which starts llama-server.

```
apps/desktop/
  src-tauri/          the shell: starts the API, opens the window, stops everything on exit
  scripts/prepare-resources.sh   freezes the API and fetches llama-server and the embedder into resources/
  resources/          (generated, gitignored) api/, llama/, embedder/
```

## Run it locally

```bash
./scripts/prepare-resources.sh macos-arm64   # or macos-x64, ubuntu-x64, win-cpu-x64
pnpm --filter @farmtwin/desktop tauri dev
```

`tauri dev` serves the web app from Vite and still starts the bundled API from `resources/`.

## Release

Push a `v*` tag. `.github/workflows/release.yml` builds Windows, Linux, Intel Mac and Apple silicon installers, attaches them to a **draft** release with `SHA256SUMS.txt` and the updater feed (`latest.json`), and leaves publishing to you. A tag with a hyphen (`v0.2.0-rc.1`) is marked as a pre-release.

Updates are signed with the Tauri updater key (separate from OS code signing). The public key is in `tauri.conf.json`; the private key belongs in the `TAURI_SIGNING_PRIVATE_KEY` repo secret and nowhere else. Without the secret the release still builds, just without updater files.

## How the pieces stop

- Closing the window: the shell posts `/api/shutdown` with a per-launch token; the API stops llama-server and exits. After 8 seconds the shell kills it anyway.
- The shell crashes or is killed: the API notices its parent is gone within 2 seconds and does the same.
- A second launch focuses the open window instead of starting a second API.
