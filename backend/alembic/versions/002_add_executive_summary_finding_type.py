"""Add executive_summary to finding_type enum.

Revision ID: 002
Revises: 001
Create Date: 2026-03-14

"""
from alembic import op

revision = "002_add_exec_summary"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE finding_type ADD VALUE IF NOT EXISTS 'executive_summary'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; downgrade is a no-op.
    pass
