"""Add HNSW vector indexes for cosine similarity search.

Improves query performance for embedding similarity searches
on property_embeddings and investor_embeddings tables.

Revision ID: 011_add_vector_indexes
Revises: 010_call_extraction_status
Create Date: 2026-02-05

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "011_add_vector_indexes"
down_revision: Union[str, None] = "010_call_extraction_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE INDEX idx_property_embeddings_hnsw
        ON property_embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    op.execute("""
        CREATE INDEX idx_investor_embeddings_hnsw
        ON investor_embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_property_embeddings_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_investor_embeddings_hnsw")
