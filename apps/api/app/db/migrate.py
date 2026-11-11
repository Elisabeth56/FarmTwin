"""Brings the database up to the latest schema at startup, keeping a backup first.

A v1 database (tables created by create_all, no alembic_version) is stamped at the
baseline so its rows are kept, then upgraded like any other.
"""

import logging
import shutil
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.config import get_settings
from app.db.session import engine

logger = logging.getLogger(__name__)

API_DIR = Path(__file__).resolve().parents[2]
BASELINE = "0001"


class MigrationError(RuntimeError):
    pass


def _alembic_config() -> Config:
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_DIR / "migrations"))
    return cfg


def run_migrations() -> None:
    db_path = get_settings().database_path
    backup = db_path.with_suffix(".db.bak")
    if db_path.exists():
        shutil.copy2(db_path, backup)

    cfg = _alembic_config()
    tables = set(inspect(engine).get_table_names())
    try:
        with engine.begin() as connection:
            cfg.attributes["connection"] = connection
            if "farms" in tables and "alembic_version" not in tables:
                logger.info("v1 database found, stamping baseline %s", BASELINE)
                command.stamp(cfg, BASELINE)
            command.upgrade(cfg, "head")
    except Exception as exc:
        logger.exception("migration failed; backup kept at %s", backup)
        raise MigrationError(
            f"FarmTwin couldn't update its database. Your data is backed up at {backup}."
        ) from exc
