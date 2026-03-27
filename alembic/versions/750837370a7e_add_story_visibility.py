"""Add visibility column to stories.

Revision ID: 750837370a7e
Revises: 98831a8e4968
Create Date: 2026-03-26
"""

import sqlalchemy as sa

from alembic import op

revision = "750837370a7e"
down_revision = "98831a8e4968"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "stories",
        sa.Column(
            "visibility",
            sa.String(20),
            nullable=False,
            server_default="close_friends",
        ),
    )
    # Set existing stories to "public" to preserve current behavior
    op.execute(
        "UPDATE stories SET visibility = 'public' WHERE visibility = 'close_friends'"
    )


def downgrade() -> None:
    op.drop_column("stories", "visibility")
