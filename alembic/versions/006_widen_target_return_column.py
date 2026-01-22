"""Widen target_return column to handle longer extracted values.

The target_return field was VARCHAR(50) but extracted return descriptions can be
longer (e.g., "25.0-26.4% IRR, 1.9x Equity Multiple, 7.3% CoC, 7.0% Pref").

Changes:
- properties.target_return: VARCHAR(50) -> VARCHAR(255)

Revision ID: 006_widen_target_return
Revises: 005_widen_columns
Create Date: 2026-01-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006_widen_target_return"
down_revision: Union[str, None] = "005_widen_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "properties",
        "target_return",
        existing_type=sa.String(50),
        type_=sa.String(255),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "properties",
        "target_return",
        existing_type=sa.String(255),
        type_=sa.String(50),
        existing_nullable=True,
    )
