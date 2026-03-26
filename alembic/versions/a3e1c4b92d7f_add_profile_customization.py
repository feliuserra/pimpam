"""add profile customization

Revision ID: a3e1c4b92d7f
Revises: fcd7dd0b83c0
Create Date: 2026-03-25 22:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3e1c4b92d7f"
down_revision: Union[str, None] = "fcd7dd0b83c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("cover_image_url", sa.String(2048), nullable=True))
    op.add_column("users", sa.Column("accent_color", sa.String(7), nullable=True))
    op.add_column("users", sa.Column("location", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("website", sa.String(500), nullable=True))
    op.add_column("users", sa.Column("pronouns", sa.String(50), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "pinned_post_id",
            sa.Integer(),
            sa.ForeignKey("posts.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("users", sa.Column("profile_layout", sa.Text(), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "show_community_stats",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "show_community_stats")
    op.drop_column("users", "profile_layout")
    op.drop_column("users", "pinned_post_id")
    op.drop_column("users", "pronouns")
    op.drop_column("users", "website")
    op.drop_column("users", "location")
    op.drop_column("users", "accent_color")
    op.drop_column("users", "cover_image_url")
