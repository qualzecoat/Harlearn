"""SQLAlchemy engine/session plumbing.

``get_db`` is a FastAPI dependency so tests can override it with an
isolated (SQLite) database without touching production configuration.

``utcnow()`` returns a *naive* UTC datetime on purpose: the slice-1
schema stores naive datetimes, and comparing aware vs naive values
raises. It avoids the deprecated ``datetime.utcnow()`` without
changing stored semantics.
"""

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from . import config

engine = create_engine(config.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
