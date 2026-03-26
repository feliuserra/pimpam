"""add hashtags

Revision ID: b4c8f2a1e3d5
Revises: a3e1c4b92d7f
Create Date: 2026-03-25 12:00:00.000000

"""

from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4c8f2a1e3d5"
down_revision: Union[str, None] = "a3e1c4b92d7f"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "hashtags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column("post_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
    )

    op.create_table(
        "post_hashtags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "post_id",
            sa.Integer(),
            sa.ForeignKey("posts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "hashtag_id",
            sa.Integer(),
            sa.ForeignKey("hashtags.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.UniqueConstraint("post_id", "hashtag_id"),
    )


def downgrade() -> None:
    op.drop_table("post_hashtags")
    op.drop_table("hashtags")
