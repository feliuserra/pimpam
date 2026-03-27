"""add_storage_quota_and_pending_deletions

Revision ID: b63251faf46c
Revises: b56a45a165d2
Create Date: 2026-03-27 02:09:09.844794
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "b63251faf46c"
down_revision: Union[str, None] = "b56a45a165d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pending_deletions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("s3_key", sa.String(length=2048), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delete_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("bytes_to_reclaim", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_pending_deletions_delete_after"),
        "pending_deletions",
        ["delete_after"],
        unique=False,
    )
    op.add_column(
        "users",
        sa.Column(
            "storage_bytes_used", sa.Integer(), server_default="0", nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "storage_bytes_used")
    op.drop_index(
        op.f("ix_pending_deletions_delete_after"), table_name="pending_deletions"
    )
    op.drop_table("pending_deletions")
