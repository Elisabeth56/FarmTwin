# apps/api

FastAPI backend for FarmTwin: farm records, crop engines, retrieval and the bridge to the local model.

## Run it

```bash
cd apps/api
cp .env.example .env          # optional: keeps dev data in ./.data
uv sync --extra ml            # ml = PyTorch embedder and Whisper, needed for retrieval and voice for now
uv run uvicorn app.main:app --reload
```

Or `pnpm dev` from the repo root to run the web app alongside it.

Settings live in `app/config.py`; any of them can be set with a `FARMTWIN_*` environment variable. The database, models and logs go in the OS app data folder unless `FARMTWIN_DATA_DIR` says otherwise.

## Checks

```bash
uv run ruff check app scripts
uv run pyright
uv run pytest
./scripts/check_no_hardcoded_paths.sh
```
