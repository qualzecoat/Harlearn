"""0002: phase 2 — graphs, frozen versions, runs, experiments.

Revision ID: 0002
Revises: 0001

Note the deliberate absence of a connections table: provider settings
live inside Model nodes (corrected spec, 2026-10-28). Model api_keys
are stored Fernet-encrypted inside graphs.nodes_json /
graph_versions.snapshot_json (config.api_key_enc), never plaintext.
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "graphs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner_id", sa.String(64), nullable=False, server_default="solo"),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("nodes_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("edges_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "graph_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("graph_id", sa.Integer(), sa.ForeignKey("graphs.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner_id", sa.String(64), nullable=False, server_default="solo"),
        sa.Column("graph_id", sa.Integer(), sa.ForeignKey("graphs.id"), nullable=False),
        sa.Column("graph_version_id", sa.Integer(), sa.ForeignKey("graph_versions.id"), nullable=False),
        sa.Column("task_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("assembled_prompt_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("output_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("token_in", sa.Integer(), nullable=True),
        sa.Column("token_out", sa.Integer(), nullable=True),
        sa.Column("usage_available", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("node_traces_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "experiments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner_id", sa.String(64), nullable=False, server_default="solo"),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "experiment_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("experiment_id", sa.Integer(), sa.ForeignKey("experiments.id"), nullable=False),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("runs.id"), nullable=False),
        sa.UniqueConstraint("experiment_id", "run_id"),
    )
    op.create_table(
        "rubric_scores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("experiment_id", sa.Integer(), sa.ForeignKey("experiments.id"), nullable=False),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("criterion", sa.String(256), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("rubric_scores")
    op.drop_table("experiment_runs")
    op.drop_table("experiments")
    op.drop_table("runs")
    op.drop_table("graph_versions")
    op.drop_table("graphs")
