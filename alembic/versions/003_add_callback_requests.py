"""Add callback_requests table for tracking callback requests.

Revision ID: 003_callbacks
Revises: 002_add_name
Create Date: 2026-01-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003_callbacks"
down_revision: Union[str, None] = "002_add_name"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create callback_requests table
    op.create_table(
        "callback_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investor_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "call_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("call_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("requested_datetime_raw", sa.String(255), nullable=False),
        sa.Column("requested_datetime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes for common queries
    op.create_index(
        "idx_callback_requests_investor_id", "callback_requests", ["investor_id"]
    )
    op.create_index("idx_callback_requests_status", "callback_requests", ["status"])
    op.create_index(
        "idx_callback_requests_datetime", "callback_requests", ["requested_datetime"]
    )


def downgrade() -> None:
    op.drop_index("idx_callback_requests_datetime", table_name="callback_requests")
    op.drop_index("idx_callback_requests_status", table_name="callback_requests")
    op.drop_index("idx_callback_requests_investor_id", table_name="callback_requests")
    op.drop_table("callback_requests")
