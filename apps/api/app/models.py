"""Slice 1 tables only: ``sessions`` and ``settings``.

Deliberately NO ``users`` table: slice 1 is a single-password gate, not a
multi-user system. Future tables (graphs, runs, experiments)
must carry ``owner_id`` with default ``'solo'`` so a later multi-user
migration does not rewrite experiment history (see ARCHITECTURE.md).
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

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


class Graph(Base):
    """Phase 2: the EDITABLE recipe. nodes/edges are JSON lists.

    Node shape: {id, type, x, y, config, disabled}
    Edge shape: {id, from_node, from_port, to_node, to_port}
    A run never references this live graph directly — see GraphVersion.
    """

    __tablename__ = "graphs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(String(64), nullable=False, default="solo")
    name = Column(String(128), nullable=False)
    nodes_json = Column(Text, nullable=False, default="[]")
    edges_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow)


class GraphVersion(Base):
    """Frozen snapshot of a graph at Run time. Immutable by convention:
    the API never updates a version row after creation."""

    __tablename__ = "graph_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    graph_id = Column(Integer, ForeignKey("graphs.id"), nullable=False)
    version = Column(Integer, nullable=False)
    snapshot_json = Column(Text, nullable=False)  # {"nodes": [...], "edges": [...]}
    content_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class Run(Base):
    """One execution of one frozen graph version."""

    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(String(64), nullable=False, default="solo")
    graph_id = Column(Integer, ForeignKey("graphs.id"), nullable=False)
    graph_version_id = Column(Integer, ForeignKey("graph_versions.id"), nullable=False)
    task_text = Column(Text, nullable=False, default="")
    assembled_prompt_json = Column(Text, nullable=False, default="[]")
    output_text = Column(Text, nullable=False, default="")
    token_in = Column(Integer, nullable=True)
    token_out = Column(Integer, nullable=True)
    usage_available = Column(Boolean, nullable=False, default=False)
    latency_ms = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="pending")
    error = Column(Text, nullable=True)
    node_traces_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, nullable=False, default=utcnow)


class Experiment(Base):
    """Hypothesis + a set of runs + a conclusion note. Notes live HERE,
    never inside a node (a note is about a comparison, not a node)."""

    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(String(64), nullable=False, default="solo")
    title = Column(String(256), nullable=False)
    hypothesis = Column(Text, nullable=False, default="")
    notes = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow)


class ExperimentRun(Base):
    __tablename__ = "experiment_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    __table_args__ = (UniqueConstraint("experiment_id", "run_id"),)


class RubricScore(Base):
    __tablename__ = "rubric_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    criterion = Column(String(256), nullable=False)
    score = Column(Integer, nullable=False)
    note = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=utcnow)


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(128), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=utcnow)
