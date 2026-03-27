"""add_shared_post_id_to_messages

Revision ID: f5f359df643b
Revises: 750837370a7e
Create Date: 2026-03-26 23:42:27.476565
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "f5f359df643b"
down_revision: Union[str, None] = "750837370a7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("shared_post_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_messages_shared_post_id",
        "messages",
        "posts",
        ["shared_post_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_messages_shared_post_id", "messages", type_="foreignkey")
    op.drop_column("messages", "shared_post_id")
