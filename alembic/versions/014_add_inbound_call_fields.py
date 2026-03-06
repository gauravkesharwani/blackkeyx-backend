"""Add inbound call support fields to call_sessions.

Revision ID: 014_add_inbound_call_fields
Revises: 013_add_voicemail_fields
Create Date: 2026-03-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014_add_inbound_call_fields"
down_revision: Union[str, None] = "013_add_voicemail_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add direction column (inbound/outbound)
    op.add_column(
        "call_sessions",
        sa.Column("direction", sa.String(20), nullable=False, server_default="outbound"),
    )
    # Add caller_phone column (for inbound calls)
    op.add_column(
        "call_sessions",
        sa.Column("caller_phone", sa.String(20), nullable=True),
    )
    # Make investor_id nullable (for unknown inbound callers)
    op.alter_column("call_sessions", "investor_id", nullable=True)


def downgrade() -> None:
    op.alter_column("call_sessions", "investor_id", nullable=False)
    op.drop_column("call_sessions", "caller_phone")
    op.drop_column("call_sessions", "direction")
