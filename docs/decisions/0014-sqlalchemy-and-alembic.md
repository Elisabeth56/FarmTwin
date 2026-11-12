# ADR-014: SQLAlchemy 2.0 with Alembic migrations, run at startup

- Status: Accepted
- Date: 2026-11-11

## Context
v1 created tables with `create_all`, which can create tables but never change them. Once FarmTwin ships updates, a user's existing database must be upgraded in place without losing farm records.

## Options
- **SQLAlchemy 2.0 + Alembic.** Already in use; Alembic is the standard migration tool for it.
- **Raw sqlite3 + hand-written SQL migrations.** Fewer dependencies, but we would rebuild versioning and ordering by hand.
- **SQLModel.** Nicer model syntax, but a thin layer over the same tools with less migration tooling.

## Decision
Keep SQLAlchemy, move models to the typed 2.0 style, and add Alembic. The backend runs `alembic upgrade head` on startup before it reports healthy, so the UI never talks to an old schema.

## Consequences
- Every schema change ships as a migration file named by intent.
- A failed migration blocks startup with a clear error instead of corrupting data. The database is copied to a `.bak` before migrating.
