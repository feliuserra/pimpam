"""add is_closed and closed_at to issues

Revision ID: bd46ffa85c2f
Revises: 83ac092e0ddd
Create Date: 2026-03-26 01:36:18.067785
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "bd46ffa85c2f"
down_revision: Union[str, None] = "83ac092e0ddd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "issues",
        sa.Column(
            "is_closed", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    op.add_column(
        "issues", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("issues", "closed_at")
    op.drop_column("issues", "is_closed")
