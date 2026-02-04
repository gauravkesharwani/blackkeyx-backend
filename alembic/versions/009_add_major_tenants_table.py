"""Add major_tenants table for generic tenant data from extraction.

This table stores the generic major tenant data extracted from deal documents.
It serves as a fallback when asset-type-specific tenant tables are empty,
particularly for mixed-use deals.

Revision ID: 009_add_major_tenants_table
Revises: 008_widen_text_columns
Create Date: 2026-02-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "009_add_major_tenants_table"
down_revision: Union[str, None] = "008_widen_text_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "major_tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tenant_name", sa.String(255), nullable=False),
        sa.Column("square_feet", sa.Integer(), nullable=True),
        sa.Column("annual_rent", sa.Numeric(15, 2), nullable=True),
        sa.Column("lease_expiration", sa.String(100), nullable=True),
        sa.Column("tenant_type", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_major_tenants_deal_id", "major_tenants", ["deal_id"])


def downgrade() -> None:
    op.drop_index("ix_major_tenants_deal_id", table_name="major_tenants")
    op.drop_table("major_tenants")
