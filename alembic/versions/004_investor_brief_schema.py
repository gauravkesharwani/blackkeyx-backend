"""Add investor brief storage schema for structured extraction and matching.

This migration adds:
- New tables: investment_metrics, financing, tenants, market_analysis,
  annual_projections, property_embeddings, investor_embeddings, investor_preferences
- New columns to properties: value_add_strategy, total_capitalization,
  sponsor_name, sponsor_track_record, extraction_confidence, extraction_notes
- New columns to deal_matches for multi-layer scoring

Revision ID: 004_investor_brief
Revises: 003_callbacks
Create Date: 2026-01-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004_investor_brief"
down_revision: Union[str, None] = "003_callbacks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ===== NEW COLUMNS ON PROPERTIES =====
    op.add_column(
        "properties",
        sa.Column("value_add_strategy", sa.Text(), nullable=True),
    )
    op.add_column(
        "properties",
        sa.Column("total_capitalization", sa.Numeric(15, 2), nullable=True),
    )
    op.add_column(
        "properties",
        sa.Column("sponsor_name", sa.String(255), nullable=True),
    )
    op.add_column(
        "properties",
        sa.Column("sponsor_track_record", sa.Text(), nullable=True),
    )
    op.add_column(
        "properties",
        sa.Column("extraction_confidence", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        "properties",
        sa.Column("extraction_notes", sa.Text(), nullable=True),
    )

    # ===== INVESTMENT_METRICS TABLE =====
    op.create_table(
        "investment_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("target_irr_min", sa.Numeric(5, 2), nullable=True),
        sa.Column("target_irr_max", sa.Numeric(5, 2), nullable=True),
        sa.Column("target_equity_multiple", sa.Numeric(5, 2), nullable=True),
        sa.Column("target_cash_on_cash", sa.Numeric(5, 2), nullable=True),
        sa.Column("cap_rate_going_in", sa.Numeric(5, 2), nullable=True),
        sa.Column("cap_rate_exit", sa.Numeric(5, 2), nullable=True),
        sa.Column("preferred_return", sa.Numeric(5, 2), nullable=True),
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # ===== FINANCING TABLE =====
    op.create_table(
        "financing",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("loan_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("ltv_ratio", sa.Numeric(5, 2), nullable=True),
        sa.Column("interest_rate", sa.Numeric(5, 3), nullable=True),
        sa.Column("loan_term_years", sa.Integer(), nullable=True),
        sa.Column("amortization_years", sa.Integer(), nullable=True),
        sa.Column("lender_name", sa.String(255), nullable=True),
        sa.Column("loan_type", sa.Text(), nullable=True),
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # ===== TENANTS TABLE =====
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tenant_name", sa.String(255), nullable=False),
        sa.Column("square_feet", sa.Integer(), nullable=True),
        sa.Column("annual_rent", sa.Numeric(12, 2), nullable=True),
        sa.Column("lease_expiration", sa.String(50), nullable=True),
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_tenants_property_id", "tenants", ["property_id"])

    # ===== MARKET_ANALYSIS TABLE =====
    op.create_table(
        "market_analysis",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("market_name", sa.String(255), nullable=True),
        sa.Column("submarket", sa.String(255), nullable=True),
        sa.Column("population_growth", sa.Text(), nullable=True),
        sa.Column(
            "employment_drivers",
            postgresql.ARRAY(sa.String),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("market_vacancy_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("market_rent_growth", sa.Text(), nullable=True),
        sa.Column("comparable_sales", sa.Text(), nullable=True),
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # ===== ANNUAL_PROJECTIONS TABLE =====
    op.create_table(
        "annual_projections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("gross_revenue", sa.Numeric(15, 2), nullable=True),
        sa.Column("effective_gross_income", sa.Numeric(15, 2), nullable=True),
        sa.Column("operating_expenses", sa.Numeric(15, 2), nullable=True),
        sa.Column("noi", sa.Numeric(15, 2), nullable=True),
        sa.Column("cash_flow", sa.Numeric(15, 2), nullable=True),
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_annual_projections_property_id", "annual_projections", ["property_id"]
    )

    # ===== PROPERTY_EMBEDDINGS TABLE (pgvector) =====
    op.create_table(
        "property_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("section_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=False),
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_property_embeddings_property_id", "property_embeddings", ["property_id"]
    )
    op.create_index(
        "idx_property_embeddings_section_type", "property_embeddings", ["section_type"]
    )

    # ===== INVESTOR_EMBEDDINGS TABLE (pgvector) =====
    op.create_table(
        "investor_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investor_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("section_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=False),
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_investor_embeddings_investor_id", "investor_embeddings", ["investor_id"]
    )
    op.create_index(
        "idx_investor_embeddings_section_type", "investor_embeddings", ["section_type"]
    )

    # ===== INVESTOR_PREFERENCES TABLE =====
    op.create_table(
        "investor_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investor_profiles.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "property_types",
            postgresql.ARRAY(sa.String),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "preferred_markets",
            postgresql.ARRAY(sa.String),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "excluded_markets",
            postgresql.ARRAY(sa.String),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("target_irr_min", sa.Numeric(5, 2), nullable=True),
        sa.Column("target_irr_max", sa.Numeric(5, 2), nullable=True),
        sa.Column("risk_tolerance_level", sa.String(50), nullable=True),
        sa.Column("investment_strategy", sa.String(50), nullable=True),
        sa.Column("hold_period_min", sa.Integer(), nullable=True),
        sa.Column("hold_period_max", sa.Integer(), nullable=True),
        sa.Column("investment_experience", sa.String(50), nullable=True),
        sa.Column("specific_concerns", sa.Text(), nullable=True),
        sa.Column(
            "preferred_structures",
            postgresql.ARRAY(sa.String),
            server_default="{}",
            nullable=False,
        ),
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # ===== ENHANCED DEAL_MATCHES COLUMNS =====
    op.add_column(
        "deal_matches",
        sa.Column("hard_filter_passed", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "deal_matches",
        sa.Column("soft_score", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        "deal_matches",
        sa.Column("semantic_score", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        "deal_matches",
        sa.Column("final_score", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        "deal_matches",
        sa.Column(
            "concerns",
            postgresql.ARRAY(sa.String),
            server_default="{}",
            nullable=True,
        ),
    )
    op.add_column(
        "deal_matches",
        sa.Column(
            "score_breakdown",
            postgresql.JSONB(),
            server_default="{}",
            nullable=True,
        ),
    )
    op.add_column(
        "deal_matches",
        sa.Column("presented_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "deal_matches",
        sa.Column("investor_response", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    # ===== REMOVE DEAL_MATCHES COLUMNS =====
    op.drop_column("deal_matches", "investor_response")
    op.drop_column("deal_matches", "presented_at")
    op.drop_column("deal_matches", "score_breakdown")
    op.drop_column("deal_matches", "concerns")
    op.drop_column("deal_matches", "final_score")
    op.drop_column("deal_matches", "semantic_score")
    op.drop_column("deal_matches", "soft_score")
    op.drop_column("deal_matches", "hard_filter_passed")

    # ===== DROP INVESTOR_PREFERENCES =====
    op.drop_table("investor_preferences")

    # ===== DROP INVESTOR_EMBEDDINGS =====
    op.drop_index("idx_investor_embeddings_section_type", table_name="investor_embeddings")
    op.drop_index("idx_investor_embeddings_investor_id", table_name="investor_embeddings")
    op.drop_table("investor_embeddings")

    # ===== DROP PROPERTY_EMBEDDINGS =====
    op.drop_index("idx_property_embeddings_section_type", table_name="property_embeddings")
    op.drop_index("idx_property_embeddings_property_id", table_name="property_embeddings")
    op.drop_table("property_embeddings")

    # ===== DROP ANNUAL_PROJECTIONS =====
    op.drop_index("idx_annual_projections_property_id", table_name="annual_projections")
    op.drop_table("annual_projections")

    # ===== DROP MARKET_ANALYSIS =====
    op.drop_table("market_analysis")

    # ===== DROP TENANTS =====
    op.drop_index("idx_tenants_property_id", table_name="tenants")
    op.drop_table("tenants")

    # ===== DROP FINANCING =====
    op.drop_table("financing")

    # ===== DROP INVESTMENT_METRICS =====
    op.drop_table("investment_metrics")

    # ===== REMOVE PROPERTIES COLUMNS =====
    op.drop_column("properties", "extraction_notes")
    op.drop_column("properties", "extraction_confidence")
    op.drop_column("properties", "sponsor_track_record")
    op.drop_column("properties", "sponsor_name")
    op.drop_column("properties", "total_capitalization")
    op.drop_column("properties", "value_add_strategy")
