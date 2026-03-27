"""migrate_image_urls_to_s3_keys

Convert existing full URLs in image columns to S3 keys by stripping
the storage_public_url prefix. This makes them compatible with the new
signed URL resolution layer.

Legacy keys (already S3 keys) are left unchanged. Only full URLs
matching the configured public URL are converted.

Revision ID: 85fe0173bef2
Revises: b63251faf46c
Create Date: 2026-03-27 02:27:18.722730
"""

import os
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "85fe0173bef2"
down_revision: Union[str, None] = "b63251faf46c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables and columns containing image URLs to convert
_IMAGE_COLUMNS = [
    ("users", "avatar_url"),
    ("users", "cover_image_url"),
    ("posts", "image_url"),
    ("post_images", "url"),
    ("stories", "image_url"),
    ("communities", "avatar_url"),
]


def _get_public_url() -> str:
    """Read the storage public URL from env (same source as config.py)."""
    return os.environ.get("STORAGE_PUBLIC_URL", "http://localhost:9000/pimpam").rstrip(
        "/"
    )


def upgrade() -> None:
    public_url = _get_public_url()
    prefix = public_url + "/"

    conn = op.get_bind()
    for table, column in _IMAGE_COLUMNS:
        # Only update rows where the column starts with the public URL prefix
        conn.execute(
            sa.text(
                f"UPDATE {table} SET {column} = SUBSTRING({column} FROM :start) "  # noqa: S608
                f"WHERE {column} LIKE :pattern"
            ),
            {"start": len(prefix) + 1, "pattern": f"{prefix}%"},
        )


def downgrade() -> None:
    public_url = _get_public_url()
    prefix = public_url + "/"

    conn = op.get_bind()
    for table, column in _IMAGE_COLUMNS:
        # Re-add the prefix to keys that don't already start with http
        conn.execute(
            sa.text(
                f"UPDATE {table} SET {column} = :prefix || {column} "  # noqa: S608
                f"WHERE {column} IS NOT NULL AND {column} NOT LIKE 'http%'"
            ),
            {"prefix": prefix},
        )
