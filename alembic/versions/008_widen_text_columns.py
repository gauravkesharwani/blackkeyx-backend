"""Widen landlord_pricing_power and return_profile from VARCHAR(50) to TEXT.

These columns hold free-form descriptive text that regularly exceeds 50 characters.

Revision ID: 008_widen_text_columns
Revises: 007_schema_redesign
Create Date: 2026-02-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008_widen_text_columns"
down_revision: Union[str, None] = "007_schema_redesign"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "market_analysis",
        "landlord_pricing_power",
        existing_type=sa.String(50),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        "investment_metrics",
        "return_profile",
        existing_type=sa.String(50),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "investment_metrics",
        "return_profile",
        existing_type=sa.Text(),
        type_=sa.String(50),
        existing_nullable=True,
    )
    op.alter_column(
        "market_analysis",
        "landlord_pricing_power",
        existing_type=sa.Text(),
        type_=sa.String(50),
        existing_nullable=True,
    )
