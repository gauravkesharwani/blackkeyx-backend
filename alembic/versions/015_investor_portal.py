"""Investor portal: investor_users, investor_subscriptions, investor_deals, deal_chunks, investor_chat_sessions.

Revision ID: 015_investor_portal
Revises: 014_add_inbound_call_fields
Create Date: 2026-03-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "015_investor_portal"
down_revision: Union[str, None] = "014_add_inbound_call_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- investor_users ---
    op.create_table(
        "investor_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("google_sub", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_investor_users_google_sub", "investor_users", ["google_sub"])
    op.create_unique_constraint("uq_investor_users_email", "investor_users", ["email"])
    op.create_index("ix_investor_users_google_sub", "investor_users", ["google_sub"])
    op.create_index("ix_investor_users_email", "investor_users", ["email"])

    # --- investor_subscriptions ---
    op.create_table(
        "investor_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investor_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("plan", sa.String(20), nullable=False, server_default="free"),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        sa.Column("stripe_price_id", sa.String(255), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint(
        "uq_investor_subscriptions_investor_user_id",
        "investor_subscriptions",
        ["investor_user_id"],
    )
    op.create_index(
        "ix_investor_subscriptions_investor_user_id",
        "investor_subscriptions",
        ["investor_user_id"],
    )
    op.create_index(
        "ix_investor_subscriptions_stripe_customer_id",
        "investor_subscriptions",
        ["stripe_customer_id"],
    )

    # --- investor_deals ---
    op.create_table(
        "investor_deals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investor_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("s3_key", sa.String(500), nullable=True),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("file_type", sa.String(10), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_investor_deals_investor_user_id", "investor_deals", ["investor_user_id"])

    # --- deal_chunks ---
    # Create with Float array first, then cast to vector(1536)
    op.create_table(
        "deal_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investor_deals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("embedding", postgresql.ARRAY(sa.Float()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # Cast to pgvector type (Alembic doesn't know Vector natively)
    op.execute(
        "ALTER TABLE deal_chunks "
        "ALTER COLUMN embedding TYPE vector(1536) "
        "USING embedding::vector(1536)"
    )
    op.create_index("ix_deal_chunks_deal_id", "deal_chunks", ["deal_id"])
    # IVFFlat index for fast approximate nearest-neighbor cosine search
    op.execute(
        "CREATE INDEX ix_deal_chunks_embedding_ivfflat "
        "ON deal_chunks USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )

    # --- investor_chat_sessions ---
    op.create_table(
        "investor_chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investor_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investor_deals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("messages", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_investor_chat_sessions_investor_user_id",
        "investor_chat_sessions",
        ["investor_user_id"],
    )
    op.create_index(
        "ix_investor_chat_sessions_deal_id",
        "investor_chat_sessions",
        ["deal_id"],
    )


def downgrade() -> None:
    op.drop_table("investor_chat_sessions")
    op.execute("DROP INDEX IF EXISTS ix_deal_chunks_embedding_ivfflat")
    op.drop_table("deal_chunks")
    op.drop_table("investor_deals")
    op.drop_table("investor_subscriptions")
    op.drop_table("investor_users")
