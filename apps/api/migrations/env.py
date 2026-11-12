"""Alembic environment: the database URL comes from app settings, never from alembic.ini."""

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.db import models  # noqa: F401  (registers tables on Base)
from app.db.session import Base

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)


def _configure_and_run(connection) -> None:
    # batch mode lets SQLite alter tables by copying them
    context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations() -> None:
    # app startup passes its own connection; the alembic CLI opens one from the URL
    connection = config.attributes.get("connection")
    if connection is not None:
        _configure_and_run(connection)
        return
    engine = engine_from_config(
        config.get_section(config.config_ini_section) or {}, prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with engine.connect() as conn:
        _configure_and_run(conn)


run_migrations()
