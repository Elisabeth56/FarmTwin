# apps/api

FastAPI backend for FarmTwin: farm records, crop engines, retrieval and the bridge to the local model.

## Run it

```bash
cd apps/api
cp .env.example .env          # optional: keeps dev data in ./.data
uv sync                       # add --extra ml for v1 voice input until whisper.cpp lands
uv run python scripts/fetch_embedder.py   # one-time download of the search model
uv run python scripts/ingest.py           # build the search index from knowledge/corpus
uv run uvicorn app.main:app --reload
```

Or `pnpm dev` from the repo root to run the web app alongside it.

Settings live in `app/config.py`; any of them can be set with a `FARMTWIN_*` environment variable. The database, models and logs go in the OS app data folder unless `FARMTWIN_DATA_DIR` says otherwise.

## Search index

The embedder (`BAAI/bge-small-en-v1.5` through fastembed) is read from `FARMTWIN_EMBEDDER_DIR`, or `models/embedder` in the data folder, and never fetched at runtime. The index records which embedder built it; if that differs from the configured one, the API refuses to start and tells you to re-run ingest. Ingest only embeds chunks that changed since the last run.

## Checks

```bash
uv run ruff check app scripts tests migrations
uv run pyright
uv run pytest
./scripts/check_no_hardcoded_paths.sh
```

## Database changes

Every schema change is a migration in `migrations/versions/`, named by intent. They run automatically when the API starts, after copying the database to `farmtwin.db.bak`. To create one:

```bash
uv run alembic revision -m "add plantings"
```
