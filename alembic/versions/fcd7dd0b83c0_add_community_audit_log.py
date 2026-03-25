"""add community audit log

Revision ID: fcd7dd0b83c0
Revises: 5b7441d30a8f
Create Date: 2026-03-25 19:09:31.010012
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "fcd7dd0b83c0"
down_revision: Union[str, None] = "5b7441d30a8f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "community_audit_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("community_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["community_id"], ["communities.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_community_audit_log_community_id"),
        "community_audit_log",
        ["community_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_community_audit_log_community_id"), table_name="community_audit_log"
    )
    op.drop_table("community_audit_log")
