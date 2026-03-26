"""add device_info to issues

Revision ID: 6afa12e768ab
Revises: 831899ad6844
Create Date: 2026-03-25 17:00:10.888355
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "6afa12e768ab"
down_revision: Union[str, None] = "831899ad6844"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("issues", sa.Column("device_info", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("issues", "device_info")
