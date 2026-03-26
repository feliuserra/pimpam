"""add show_posts_on_profile to users

Revision ID: 83ac092e0ddd
Revises: 4c2618d3b4a6
Create Date: 2026-03-25 23:58:15.048256
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "83ac092e0ddd"
down_revision: Union[str, None] = "4c2618d3b4a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "show_posts_on_profile",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "show_posts_on_profile")
