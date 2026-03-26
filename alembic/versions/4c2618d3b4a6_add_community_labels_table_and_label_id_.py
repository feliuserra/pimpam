"""add community_labels table and label_id on posts

Revision ID: 4c2618d3b4a6
Revises: b4c8f2a1e3d5
Create Date: 2026-03-25 23:17:11.143051
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "4c2618d3b4a6"
down_revision: Union[str, None] = "b4c8f2a1e3d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "community_labels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("community_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=True),
        sa.Column("description", sa.String(length=200), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["community_id"], ["communities.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("community_id", "name"),
    )
    op.create_index(
        op.f("ix_community_labels_community_id"),
        "community_labels",
        ["community_id"],
        unique=False,
    )
    op.add_column("posts", sa.Column("label_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_posts_label_id",
        "posts",
        "community_labels",
        ["label_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_posts_label_id", "posts", type_="foreignkey")
    op.drop_column("posts", "label_id")
    op.drop_index(
        op.f("ix_community_labels_community_id"), table_name="community_labels"
    )
    op.drop_table("community_labels")
