from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

try:
    import sqlite_vec
except ImportError:
    sqlite_vec = None

SQLALCHEMY_DATABASE_URL = "sqlite:///./farmtwin.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _load_sqlite_vec(dbapi_connection, connection_record):
    if sqlite_vec is None:
        return
    try:
        dbapi_connection.enable_load_extension(True)
        sqlite_vec.load(dbapi_connection)
        dbapi_connection.enable_load_extension(False)
    except Exception:
        # sqlite-vec is only needed from Day 2 onward; ignore load failures for now.
        pass


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
