"""Initial schema creation.

Revision ID: 001_initial
Revises:
Create Date: 2026-01-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension (for future embedding support)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create investor_profiles table
    op.create_table(
        "investor_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("timeline", sa.String(50), nullable=True),
        sa.Column("capital_available", sa.Integer(), nullable=True),
        sa.Column(
            "investment_preferences",
            postgresql.ARRAY(sa.String()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("investment_thesis", sa.Text(), nullable=True),
        sa.Column("risk_tolerance", sa.String(50), nullable=True),
        sa.Column("stage", sa.String(50), server_default="new_lead", nullable=False),
        sa.Column("lead_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("source", sa.String(50), server_default="web", nullable=False),
        sa.Column("investor_type", sa.String(100), nullable=True),
        sa.Column("capacity", sa.String(100), nullable=True),
        sa.Column("fit", sa.String(100), nullable=True),
        sa.Column("process", sa.String(100), nullable=True),
        sa.Column("timing", sa.String(100), nullable=True),
        sa.Column("qualification_bucket", sa.String(50), nullable=True),
        sa.Column("qualification_score", sa.Integer(), nullable=True),
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
    op.create_index("idx_investor_profiles_stage", "investor_profiles", ["stage"])
    op.create_index("idx_investor_profiles_lead_score", "investor_profiles", ["lead_score"])
    op.create_index("idx_investor_profiles_phone", "investor_profiles", ["phone"])

    # Create properties table
    op.create_table(
        "properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("deal_type", sa.String(50), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("thesis", sa.Text(), nullable=True),
        sa.Column("minimum_investment", sa.Integer(), nullable=True),
        sa.Column("target_return", sa.String(50), nullable=True),
        sa.Column(
            "risk_factors",
            postgresql.ARRAY(sa.String()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("ideal_investor_profile", sa.Text(), nullable=True),
        sa.Column("structure", sa.String(50), nullable=True),
        sa.Column("timeline", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(50), nullable=True),
        sa.Column("zip_code", sa.String(20), nullable=True),
        sa.Column("purchase_price", sa.Integer(), nullable=True),
        sa.Column("square_feet", sa.Integer(), nullable=True),
        sa.Column("total_equity_required", sa.Integer(), nullable=True),
        sa.Column("document_s3_key", sa.String(500), nullable=True),
        sa.Column("document_filename", sa.String(255), nullable=True),
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
    op.create_index("idx_properties_status", "properties", ["status"])
    op.create_index("idx_properties_deal_type", "properties", ["deal_type"])

    # Create property_features table
    op.create_table(
        "property_features",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("asset_type", sa.String(50), nullable=False),
        sa.Column(
            "features", postgresql.JSONB(), server_default="{}", nullable=False
        ),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("year_renovated", sa.Integer(), nullable=True),
        sa.Column("parking_spaces", sa.Integer(), nullable=True),
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
    op.create_index(
        "idx_property_features_jsonb",
        "property_features",
        ["features"],
        postgresql_using="gin",
    )

    # Create property_documents table
    op.create_table(
        "property_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("s3_key", sa.String(500), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column(
            "extraction_status",
            sa.String(50),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("extracted_text", sa.Text(), nullable=True),
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

    # Create consents table
    op.create_table(
        "consents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investor_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("consent_text", sa.Text(), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create lead_notes table
    op.create_table(
        "lead_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investor_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(100), server_default="admin", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_lead_notes_investor_id", "lead_notes", ["investor_id"])

    # Create stage_history table
    op.create_table(
        "stage_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investor_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_stage", sa.String(50), nullable=True),
        sa.Column("to_stage", sa.String(50), nullable=False),
        sa.Column("changed_by", sa.String(100), server_default="system", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_stage_history_investor_id", "stage_history", ["investor_id"])

    # Create deal_matches table
    op.create_table(
        "deal_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investor_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "similarity_score", sa.Numeric(5, 4), server_default="0", nullable=False
        ),
        sa.Column(
            "match_reasons",
            postgresql.ARRAY(sa.String()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_deal_matches_investor_id", "deal_matches", ["investor_id"])
    op.create_index("idx_deal_matches_property_id", "deal_matches", ["property_id"])

    # Create call_sessions table
    op.create_table(
        "call_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investor_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status", sa.String(50), server_default="initiated", nullable=False
        ),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("recording_url", sa.String(500), nullable=True),
        sa.Column("room_name", sa.String(255), nullable=True),
        sa.Column("livekit_participant_id", sa.String(255), nullable=True),
        sa.Column(
            "initiated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_call_sessions_investor_id", "call_sessions", ["investor_id"])
    op.create_index("idx_call_sessions_status", "call_sessions", ["status"])

    # Create call_transcripts table
    op.create_table(
        "call_transcripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "call_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("call_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("speaker", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("start_time", sa.Integer(), nullable=True),
        sa.Column("end_time", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("call_transcripts")
    op.drop_table("call_sessions")
    op.drop_table("deal_matches")
    op.drop_table("stage_history")
    op.drop_table("lead_notes")
    op.drop_table("consents")
    op.drop_table("property_documents")
    op.drop_table("property_features")
    op.drop_table("properties")
    op.drop_table("investor_profiles")
    op.execute("DROP EXTENSION IF EXISTS vector")
