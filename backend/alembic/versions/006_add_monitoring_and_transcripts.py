"""Add portfolio monitoring schedules and expert transcripts tables.

Revision ID: 006
Revises: 005
Create Date: 2026-03-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Portfolio monitoring schedules ────────────────────────────────────────
    op.create_table(
        "monitoring_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "engagement_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("engagements.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("user_id", sa.String(255), nullable=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        # cron expression e.g. "0 9 1 * *" (first of month at 9am)
        sa.Column("cron_expression", sa.String(100), nullable=True),
        # monthly | quarterly | weekly | manual
        sa.Column("frequency", sa.String(50), nullable=False, server_default="monthly"),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
        # Metrics to monitor — JSON array of source system names
        sa.Column("sources", postgresql.JSONB, nullable=True),
        # Baseline snapshot captured at acquisition (findings JSON)
        sa.Column("baseline_snapshot", postgresql.JSONB, nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── Monitoring runs (individual executions) ────────────────────────────────
    op.create_table(
        "monitoring_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "schedule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("monitoring_schedules.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "engagement_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("engagements.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # pending | running | completed | failed
        sa.Column("status", sa.String(20), nullable=False, server_default="pending", index=True),
        # Delta findings vs baseline: JSON array of {metric, baseline, current, delta_pct, flag}
        sa.Column("deltas", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=True,
        ),
        sa.Column(
            "completed_at", sa.DateTime(timezone=True), nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── Expert call transcripts ───────────────────────────────────────────────
    op.create_table(
        "expert_transcripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "engagement_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("engagements.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("user_id", sa.String(255), nullable=True, index=True),
        # tegus | third_bridge | manual_upload
        sa.Column("source", sa.String(50), nullable=False, server_default="manual_upload"),
        # External ID from Tegus/Third Bridge for dedup
        sa.Column("external_id", sa.String(255), nullable=True, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("expert_name", sa.String(255), nullable=True),
        sa.Column("expert_role", sa.String(255), nullable=True),
        sa.Column("call_date", sa.Date, nullable=True),
        sa.Column("company_name", sa.String(255), nullable=True),
        sa.Column("transcript_text", sa.Text, nullable=True),
        # LLM-extracted sentiment and key themes from transcript
        sa.Column("sentiment", sa.String(20), nullable=True),   # positive | neutral | negative
        sa.Column("key_themes", postgresql.JSONB, nullable=True),  # list of strings
        sa.Column("extracted_insights", sa.Text, nullable=True),
        sa.Column("file_size_bytes", sa.Integer, nullable=True),
        # processing | ready | error
        sa.Column("status", sa.String(20), nullable=False, server_default="processing", index=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("expert_transcripts")
    op.drop_table("monitoring_runs")
    op.drop_table("monitoring_schedules")
