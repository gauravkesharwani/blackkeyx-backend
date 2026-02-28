"""Add timezone column to investor_profiles.

Stores IANA timezone string (e.g. 'America/New_York') confirmed
during voice calls. Used by the callback scheduler to dispatch
follow-up calls at the correct local time.

Revision ID: 012_add_investor_timezone
Revises: 011_add_vector_indexes
Create Date: 2026-02-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "012_add_investor_timezone"
down_revision: Union[str, None] = "011_add_vector_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("investor_profiles", sa.Column("timezone", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("investor_profiles", "timezone")
