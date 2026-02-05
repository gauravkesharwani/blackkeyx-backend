"""Add extraction status fields to call_sessions table.

Tracks the status of LLM-based insight extraction from call transcripts.

Revision ID: 010_call_extraction_status
Revises: 009_add_major_tenants_table
Create Date: 2026-02-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010_call_extraction_status"
down_revision: Union[str, None] = "009_add_major_tenants_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add extraction status tracking columns to call_sessions
    op.add_column(
        "call_sessions",
        sa.Column("extraction_status", sa.String(50), nullable=True),
    )
    op.add_column(
        "call_sessions",
        sa.Column("extraction_confidence", sa.Numeric(3, 2), nullable=True),
    )
    op.add_column(
        "call_sessions",
        sa.Column("extraction_summary", sa.Text(), nullable=True),
    )
    op.add_column(
        "call_sessions",
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("call_sessions", "extracted_at")
    op.drop_column("call_sessions", "extraction_summary")
    op.drop_column("call_sessions", "extraction_confidence")
    op.drop_column("call_sessions", "extraction_status")
