"""001 — Initial schema

Creates all core tables for the KEEN multi-agent system.

Revision ID: 001_initial
Revises: None
Create Date: 2026-03-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enum types ───────────────────────────────────────
    engagement_status = postgresql.ENUM(
        "draft", "running", "paused", "completed", "failed",
        name="engagement_status",
        create_type=True,
    )
    agent_type = postgresql.ENUM(
        "research", "analysis", "delivery",
        name="agent_type",
        create_type=True,
    )
    agent_run_status = postgresql.ENUM(
        "queued", "running", "checkpointed", "completed", "failed", "paused",
        name="agent_run_status",
        create_type=True,
    )
    credential_type = postgresql.ENUM(
        "api_key", "oauth", "username_password", "sso", "token",
        name="credential_type",
        create_type=True,
    )
    finding_type = postgresql.ENUM(
        "data_point", "discrepancy", "exception", "insight",
        name="finding_type",
        create_type=True,
    )
    finding_severity = postgresql.ENUM(
        "info", "warning", "critical",
        name="finding_severity",
        create_type=True,
    )

    # ── Leads ────────────────────────────────────────────
    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, index=True),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("aum_range", sa.String(100), nullable=True),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Engagements ──────────────────────────────────────
    op.create_table(
        "engagements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_name", sa.String(255), nullable=False, index=True),
        sa.Column("target_company", sa.String(255), nullable=True),
        sa.Column("pe_firm", sa.String(255), nullable=True),
        sa.Column("deal_size", sa.String(100), nullable=True),
        sa.Column("engagement_type", sa.String(100), server_default="full_diligence"),
        sa.Column("status", engagement_status, server_default="draft", nullable=False, index=True),
        sa.Column("config", postgresql.JSONB, server_default="{}"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Agent Runs ───────────────────────────────────────
    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("engagement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("agent_type", agent_type, nullable=False),
        sa.Column("status", agent_run_status, server_default="queued", nullable=False, index=True),
        sa.Column("current_step", sa.Integer, server_default="0"),
        sa.Column("total_steps", sa.Integer, server_default="0"),
        sa.Column("progress_pct", sa.Float, server_default="0.0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Checkpoints ──────────────────────────────────────
    op.create_table(
        "checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("step_index", sa.Integer, nullable=False),
        sa.Column("state_data", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Credentials ──────────────────────────────────────
    op.create_table(
        "credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("engagement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("system_name", sa.String(100), nullable=False, index=True),
        sa.Column("credential_type", credential_type, nullable=False),
        sa.Column("encrypted_data", sa.LargeBinary, nullable=False),
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Findings ─────────────────────────────────────────
    op.create_table(
        "findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("finding_type", finding_type, nullable=False),
        sa.Column("source_system", sa.String(100), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("data", postgresql.JSONB, server_default="{}"),
        sa.Column("severity", finding_severity, server_default="info", nullable=False),
        sa.Column("requires_human_review", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("findings")
    op.drop_table("credentials")
    op.drop_table("checkpoints")
    op.drop_table("agent_runs")
    op.drop_table("engagements")
    op.drop_table("leads")

    op.execute("DROP TYPE IF EXISTS finding_severity")
    op.execute("DROP TYPE IF EXISTS finding_type")
    op.execute("DROP TYPE IF EXISTS credential_type")
    op.execute("DROP TYPE IF EXISTS agent_run_status")
    op.execute("DROP TYPE IF EXISTS agent_type")
    op.execute("DROP TYPE IF EXISTS engagement_status")
