"""Widen structure and timeline columns to handle longer extracted values.

The structure field was VARCHAR(50) but extracted deal structures can be
much longer (e.g., "Single purpose limited liability company (OP Burlington
Drive, LLC) co-investing alongside institutional equity partner...").

Changes:
- properties.structure: VARCHAR(50) -> TEXT
- properties.timeline: VARCHAR(50) -> VARCHAR(100)

Revision ID: 005_widen_columns
Revises: 004_investor_brief
Create Date: 2026-01-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_widen_columns"
down_revision: Union[str, None] = "004_investor_brief"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change structure from VARCHAR(50) to TEXT
    op.alter_column(
        "properties",
        "structure",
        existing_type=sa.String(50),
        type_=sa.Text(),
        existing_nullable=True,
    )

    # Change timeline from VARCHAR(50) to VARCHAR(100)
    op.alter_column(
        "properties",
        "timeline",
        existing_type=sa.String(50),
        type_=sa.String(100),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Revert timeline to VARCHAR(50)
    op.alter_column(
        "properties",
        "timeline",
        existing_type=sa.String(100),
        type_=sa.String(50),
        existing_nullable=True,
    )

    # Revert structure to VARCHAR(50)
    op.alter_column(
        "properties",
        "structure",
        existing_type=sa.Text(),
        type_=sa.String(50),
        existing_nullable=True,
    )
