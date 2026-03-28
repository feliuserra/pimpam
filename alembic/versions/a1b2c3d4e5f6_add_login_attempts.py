"""add_login_attempts

Revision ID: a1b2c3d4e5f6
Revises: f5f359df643b
Create Date: 2026-03-27 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "f5f359df643b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "login_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_login_attempts_created_at", "login_attempts", ["created_at"])
    op.create_index("ix_login_attempts_ip_hash", "login_attempts", ["ip_hash"])
    op.create_index(
        "ix_login_attempts_ip_hash_success_created",
        "login_attempts",
        ["ip_hash", "success", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_login_attempts_ip_hash_success_created", table_name="login_attempts"
    )
    op.drop_index("ix_login_attempts_ip_hash", table_name="login_attempts")
    op.drop_index("ix_login_attempts_created_at", table_name="login_attempts")
    op.drop_table("login_attempts")
