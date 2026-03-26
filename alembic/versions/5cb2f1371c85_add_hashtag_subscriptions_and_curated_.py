"""add hashtag subscriptions and curated picks

Revision ID: 5cb2f1371c85
Revises: bd46ffa85c2f
Create Date: 2026-03-26 10:57:18.423841
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "5cb2f1371c85"
down_revision: Union[str, None] = "bd46ffa85c2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "curated_picks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("community_id", sa.Integer(), nullable=False),
        sa.Column("curator_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["community_id"], ["communities.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["curator_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "community_id"),
    )
    op.create_index(
        op.f("ix_curated_picks_community_id"),
        "curated_picks",
        ["community_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_curated_picks_created_at"),
        "curated_picks",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_curated_picks_post_id"), "curated_picks", ["post_id"], unique=False
    )
    op.create_table(
        "hashtag_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("hashtag_id", sa.Integer(), nullable=False),
        sa.Column("subscribed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["hashtag_id"], ["hashtags.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "hashtag_id"),
    )
    op.create_index(
        op.f("ix_hashtag_subscriptions_hashtag_id"),
        "hashtag_subscriptions",
        ["hashtag_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_hashtag_subscriptions_user_id"),
        "hashtag_subscriptions",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_hashtag_subscriptions_user_id"), table_name="hashtag_subscriptions"
    )
    op.drop_index(
        op.f("ix_hashtag_subscriptions_hashtag_id"), table_name="hashtag_subscriptions"
    )
    op.drop_table("hashtag_subscriptions")
    op.drop_index(op.f("ix_curated_picks_post_id"), table_name="curated_picks")
    op.drop_index(op.f("ix_curated_picks_created_at"), table_name="curated_picks")
    op.drop_index(op.f("ix_curated_picks_community_id"), table_name="curated_picks")
    op.drop_table("curated_picks")
