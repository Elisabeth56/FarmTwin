import sqlite3

import pytest
from sqlalchemy import create_engine, inspect

V1_SCHEMA = """
CREATE TABLE farms (id INTEGER PRIMARY KEY, name VARCHAR NOT NULL, region VARCHAR, latitude FLOAT,
  longitude FLOAT, area_hectares FLOAT, created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL);
CREATE TABLE fields (id INTEGER PRIMARY KEY, farm_id INTEGER NOT NULL REFERENCES farms(id), name VARCHAR NOT NULL,
  area_hectares FLOAT, soil_type VARCHAR, soil_ph_estimate FLOAT, notes TEXT);
CREATE TABLE crops (id INTEGER PRIMARY KEY, field_id INTEGER NOT NULL REFERENCES fields(id), crop_type VARCHAR NOT NULL,
  variety VARCHAR, planting_date DATE, status VARCHAR, created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL);
CREATE TABLE observations (id INTEGER PRIMARY KEY, field_id INTEGER NOT NULL, obs_type VARCHAR NOT NULL, value_numeric FLOAT,
  value_text TEXT, unit VARCHAR, observed_at DATETIME NOT NULL, created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL);
CREATE TABLE weather_snapshots (id INTEGER PRIMARY KEY, farm_id INTEGER NOT NULL, snapshot_date DATE NOT NULL,
  rainfall_mm FLOAT, temp_min_c FLOAT, temp_max_c FLOAT, humidity_pct FLOAT, notes TEXT);
CREATE TABLE recommendations (id INTEGER PRIMARY KEY, farm_id INTEGER NOT NULL, field_id INTEGER, what TEXT NOT NULL,
  why TEXT, when_urgency VARCHAR, risk_if_ignored TEXT, priority INTEGER, cited_chunk_ids TEXT, model_name VARCHAR,
  created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL);
CREATE TABLE document_chunks (id INTEGER PRIMARY KEY, source_id VARCHAR, source_title VARCHAR, source_org VARCHAR,
  source_url VARCHAR, source_note TEXT, region VARCHAR, crop VARCHAR, topics TEXT, chunk_title VARCHAR,
  token_count INTEGER, content TEXT NOT NULL);
INSERT INTO farms (id, name, region) VALUES (1, 'Adamu''s farm', 'Kaduna');
INSERT INTO fields (id, farm_id, name) VALUES (1, 1, 'Main field');
INSERT INTO crops (id, field_id, crop_type, planting_date, status) VALUES (1, 1, 'maize', '2026-06-01', 'active');
"""


@pytest.fixture()
def fresh_data_dir(tmp_path, monkeypatch):
    """Points settings and the engine at an empty folder for one test."""
    from app import config
    from app.db import migrate, session

    monkeypatch.setenv("FARMTWIN_DATA_DIR", str(tmp_path))
    config.get_settings.cache_clear()
    engine = create_engine(config.get_settings().database_url)
    monkeypatch.setattr(session, "engine", engine)
    monkeypatch.setattr(migrate, "engine", engine)
    yield tmp_path
    engine.dispose()
    config.get_settings.cache_clear()


def test_fresh_database_gets_every_table(fresh_data_dir):
    from app.db.migrate import run_migrations

    run_migrations()
    db = fresh_data_dir / "farmtwin.db"
    tables = set(inspect(create_engine(f"sqlite:///{db}")).get_table_names())
    assert {"farms", "fields", "plantings", "observations", "alembic_version"} <= tables
    assert "crops" not in tables


def test_v1_database_keeps_its_rows(fresh_data_dir):
    from app.db.migrate import run_migrations

    db = fresh_data_dir / "farmtwin.db"
    with sqlite3.connect(db) as conn:
        conn.executescript(V1_SCHEMA)

    run_migrations()

    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT name FROM farms").fetchall() == [("Adamu's farm",)]
        assert conn.execute("SELECT crop_type FROM plantings").fetchall() == [("maize",)]
        assert conn.execute("SELECT version_num FROM alembic_version").fetchone() is not None
    assert (fresh_data_dir / "farmtwin.db.bak").exists()


def test_failed_migration_keeps_the_backup(fresh_data_dir, monkeypatch):
    from alembic import command

    from app.db import migrate

    db = fresh_data_dir / "farmtwin.db"
    with sqlite3.connect(db) as conn:
        conn.executescript(V1_SCHEMA)

    def broken(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(command, "upgrade", broken)
    with pytest.raises(migrate.MigrationError, match="backed up"):
        migrate.run_migrations()
    assert (fresh_data_dir / "farmtwin.db.bak").exists()
