"""Add voicemail detection fields to call_sessions.

Adds voicemail_detected, voicemail_confidence, voicemail_message_left,
and retry_count columns for voicemail detection and retry handling.

Revision ID: 013_add_voicemail_fields
Revises: 012_add_investor_timezone
Create Date: 2026-02-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "013_add_voicemail_fields"
down_revision: Union[str, None] = "012_add_investor_timezone"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "call_sessions",
        sa.Column("voicemail_detected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "call_sessions",
        sa.Column("voicemail_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "call_sessions",
        sa.Column("voicemail_message_left", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "call_sessions",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("call_sessions", "retry_count")
    op.drop_column("call_sessions", "voicemail_message_left")
    op.drop_column("call_sessions", "voicemail_confidence")
    op.drop_column("call_sessions", "voicemail_detected")
