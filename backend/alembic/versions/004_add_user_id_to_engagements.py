"""Add user_id to engagements for per-user data isolation.

Revision ID: 004
Revises: 003
Create Date: 2025-06-01
"""

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add nullable user_id so existing rows are preserved (legacy = visible to all)
    op.add_column(
        "engagements",
        sa.Column("user_id", sa.String(length=255), nullable=True),
    )
    # Index for fast per-user queries
    op.create_index(
        "ix_engagements_user_id",
        "engagements",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_engagements_user_id", table_name="engagements")
    op.drop_column("engagements", "user_id")
