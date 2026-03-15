"""Add flag to finding_type enum.

Revision ID: 003
Revises: 002_add_exec_summary
Create Date: 2026-03-15

"""
from alembic import op

revision = "003_add_flag"
down_revision = "002_add_exec_summary"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE finding_type ADD VALUE IF NOT EXISTS 'flag'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; downgrade is a no-op.
    pass
