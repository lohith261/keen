"""Add primary_research, external_records, legal_findings, technical_dd_reports tables.

Revision ID: 007
Revises: 006
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Primary research records (P4 — Commercial DD) ──────────────────────────
    op.create_table(
        "primary_research",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "engagement_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("engagements.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("user_id", sa.String(255), nullable=True, index=True),
        sa.Column(
            "type",
            sa.Enum(
                "customer_interview",
                "channel_check",
                "win_loss",
                "market_sizing",
                name="primary_research_type",
            ),
            nullable=False,
            index=True,
        ),
        sa.Column("company_name", sa.String(500), nullable=False),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("contact_role", sa.String(255), nullable=True),
        sa.Column("interview_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("sentiment", sa.String(20), nullable=True),
        sa.Column("key_themes", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("action_items", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft", index=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── External verification records (P5) ─────────────────────────────────────
    op.create_table(
        "external_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "engagement_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("engagements.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("user_id", sa.String(255), nullable=True, index=True),
        sa.Column(
            "source",
            sa.Enum(
                "courtlistener",
                "uspto",
                "ucc",
                "bank_statement",
                name="external_record_source",
            ),
            nullable=False,
            index=True,
        ),
        sa.Column("record_type", sa.String(100), nullable=False),
        sa.Column("external_id", sa.String(500), nullable=True),
        sa.Column("title", sa.String(1000), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("url", sa.String(2000), nullable=True),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="info", index=True),
        sa.Column("raw_data", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("corroborates_finding", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── Legal findings from contract analysis (P7) ─────────────────────────────
    op.create_table(
        "legal_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "engagement_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("engagements.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("user_id", sa.String(255), nullable=True, index=True),
        sa.Column("clause_type", sa.String(50), nullable=False, index=True),
        sa.Column("text_excerpt", sa.Text, nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="info"),
        sa.Column("requires_review", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("reviewed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── Technical DD reports from GitHub analysis (P8) ─────────────────────────
    op.create_table(
        "technical_dd_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "engagement_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("engagements.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("user_id", sa.String(255), nullable=True, index=True),
        sa.Column("repo_url", sa.String(500), nullable=True),
        sa.Column("language_stats", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("contributor_count", sa.Integer, nullable=True),
        sa.Column("bus_factor", sa.Integer, nullable=True),
        sa.Column("commit_velocity", sa.Float, nullable=True),
        sa.Column("open_issues_count", sa.Integer, nullable=True),
        sa.Column("security_vulnerabilities", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("dependency_risks", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("health_score", sa.Float, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending", index=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("technical_dd_reports")
    op.drop_table("legal_findings")
    op.drop_table("external_records")
    op.drop_table("primary_research")
    op.execute("DROP TYPE IF EXISTS primary_research_type")
    op.execute("DROP TYPE IF EXISTS external_record_source")
