"""Session lifecycle helpers (create / load / revoke)."""

from datetime import datetime, timedelta, timedelta

from sqlalchemy.orm import Session as DbSession

from . import config, security
from .db import utcnow
from .models import Session as SessionRow


def create_session(db: DbSession):
    raw_token = security.new_token()
    row = SessionRow(
        token_hash=security.hash_token(raw_token),
        csrf_token=security.new_csrf_token(),
        created_at=utcnow(),
        expires_at=utcnow() + timedelta(days=config.SESSION_TTL_DAYS),
        last_seen_at=utcnow(),
    )
    db.add(row)
    db.commit()
    return raw_token, row


def load_session(db: DbSession, raw_token: str):
    """Return the session row if it exists and has not expired, else None."""
    if not raw_token:
        return None
    row = (
        db.query(SessionRow)
        .filter(SessionRow.token_hash == security.hash_token(raw_token))
        .first()
    )
    if row is None:
        return None
    if row.expires_at <= utcnow():
        db.delete(row)
        db.commit()
        return None
    row.last_seen_at = utcnow()
    db.commit()
    return row


def revoke_session(db: DbSession, raw_token: str) -> None:
    if not raw_token:
        return
    row = (
        db.query(SessionRow)
        .filter(SessionRow.token_hash == security.hash_token(raw_token))
        .first()
    )
    if row is not None:
        db.delete(row)
        db.commit()
