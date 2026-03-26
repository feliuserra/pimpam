"""add avatar_url to communities

Revision ID: 5b7441d30a8f
Revises: 6afa12e768ab
Create Date: 2026-03-25 17:19:06.816385
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "5b7441d30a8f"
down_revision: Union[str, None] = "6afa12e768ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "communities", sa.Column("avatar_url", sa.String(length=500), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("communities", "avatar_url")
