"""merge_heads

Revision ID: b56a45a165d2
Revises: 56a708a8ec9b, f5f359df643b
Create Date: 2026-03-27 02:08:11.444207
"""

from typing import Sequence, Union

revision: str = "b56a45a165d2"
down_revision: Union[str, None] = ("56a708a8ec9b", "f5f359df643b")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
