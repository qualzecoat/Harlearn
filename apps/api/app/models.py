"""Slice 1 tables only: ``sessions`` and ``settings``.

Deliberately NO ``users`` table: slice 1 is a single-password gate, not a
multi-user system. Future tables (graphs, runs, experiments, connections)
must carry ``owner_id`` with default ``'solo'`` so a later multi-user
migration does not rewrite experiment history (see ARCHITECTURE.md).
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text

from .db import Base, utcnow


class Session(Base):
    __tablename__ = "sessions"

    # SHA-256 hex of the raw session token. The raw token only ever lives
    # in the HttpOnly cookie; the database never stores it in cleartext.
    token_hash = Column(String(64), primary_key=True)
    csrf_token = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_seen_at = Column(DateTime, nullable=False, default=utcnow)


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(128), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=utcnow)
