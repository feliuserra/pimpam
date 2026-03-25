"""add_admin_layer_models

Revision ID: 1e64021bf12e
Revises: 2fe7e8648676
Create Date: 2026-03-25 15:29:50.386960
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "1e64021bf12e"
down_revision: Union[str, None] = "2fe7e8648676"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_admin column to users
    op.add_column(
        "users",
        sa.Column(
            "is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )

    # Global bans (platform-wide, permanent)
    op.create_table(
        "global_bans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("banned_by_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["banned_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_global_bans_user_id", "global_bans", ["user_id"], unique=True)

    # User suspensions (temporary, with expiry)
    op.create_table(
        "user_suspensions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("suspended_by_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["suspended_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_suspensions_user_id", "user_suspensions", ["user_id"])
    op.create_index("ix_user_suspensions_is_active", "user_suspensions", ["is_active"])

    # Admin content removals (audit log for posts/comments removed by admins)
    op.create_table(
        "admin_content_removals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(10), nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add status column to reports for admin review tracking
    op.add_column(
        "reports",
        sa.Column(
            "status", sa.String(20), nullable=False, server_default=sa.text("'pending'")
        ),
    )
    op.add_column("reports", sa.Column("resolved_by_id", sa.Integer(), nullable=True))
    op.add_column(
        "reports", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_foreign_key(
        "fk_reports_resolved_by", "reports", "users", ["resolved_by_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_reports_resolved_by", "reports", type_="foreignkey")
    op.drop_column("reports", "resolved_at")
    op.drop_column("reports", "resolved_by_id")
    op.drop_column("reports", "status")
    op.drop_table("admin_content_removals")
    op.drop_index("ix_user_suspensions_is_active", table_name="user_suspensions")
    op.drop_index("ix_user_suspensions_user_id", table_name="user_suspensions")
    op.drop_table("user_suspensions")
    op.drop_index("ix_global_bans_user_id", table_name="global_bans")
    op.drop_table("global_bans")
    op.drop_column("users", "is_admin")
