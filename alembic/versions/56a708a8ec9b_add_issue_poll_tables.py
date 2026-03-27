"""add_issue_poll_tables

Revision ID: 56a708a8ec9b
Revises: 98831a8e4968
Create Date: 2026-03-27 01:09:06.744528
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "56a708a8ec9b"
down_revision: Union[str, None] = "98831a8e4968"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "issue_polls",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("issue_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.String(length=300), nullable=False),
        sa.Column("allows_multiple", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("issue_id"),
    )
    op.create_table(
        "issue_poll_options",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("poll_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(length=200), nullable=False),
        sa.Column("vote_count", sa.Integer(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["poll_id"], ["issue_polls.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_issue_poll_options_poll_id"),
        "issue_poll_options",
        ["poll_id"],
        unique=False,
    )
    op.create_table(
        "issue_poll_votes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("option_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["option_id"], ["issue_poll_options.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("option_id", "user_id"),
    )
    op.create_index(
        op.f("ix_issue_poll_votes_option_id"),
        "issue_poll_votes",
        ["option_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_issue_poll_votes_option_id"), table_name="issue_poll_votes")
    op.drop_table("issue_poll_votes")
    op.drop_index(
        op.f("ix_issue_poll_options_poll_id"), table_name="issue_poll_options"
    )
    op.drop_table("issue_poll_options")
    op.drop_table("issue_polls")
