# ADR-013: SQLite with sqlite-vec and FTS5 as the only data store

- Status: Accepted
- Date: 2026-11-11

## Context
FarmTwin v2 runs on one laptop, for one officer, offline. Data is small and relational: farms, fields, plantings, observations, weather, recommendations, plus 400–600 knowledge chunks with vectors. One writer at a time. The main reads are a farm dashboard (farm, fields, active plantings, last 30 days of observations, latest weather) and a crop-filtered knowledge search.

## Options
- **SQLite + sqlite-vec + FTS5.** One file, embedded, vector and keyword search in the same database.
- **DuckDB.** Strong for analytics; nothing here is analytical, and its vector support is less mature than sqlite-vec for this use.
- **LanceDB or Chroma.** Good vector stores, but farm records would still need a second database.

## Decision
SQLite with sqlite-vec for vectors and FTS5 for keyword search. The database lives in the OS app data folder, not next to the app.

## Consequences
- Backup and export is copying one file.
- Hybrid search (ADR-018) is one SQL query.
- No concurrent writers. That matches a single-user desktop app; it would not survive a move to a shared server.
