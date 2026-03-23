"""
Meilisearch integration — full-text search over posts.

Works with any Meilisearch v1.x instance. In development the server runs via
docker-compose (port 7700) with no auth. In production, set SEARCH_API_KEY to
your master key.

All indexing is fire-and-forget: if Meilisearch is unavailable, post create/edit/
delete operations succeed normally and the search index is simply out of sync
until the service recovers.
"""
import asyncio

import meilisearch

from app.core.config import settings

_INDEX = "posts"


def get_client() -> meilisearch.Client:
    return meilisearch.Client(settings.search_url, settings.search_api_key or None)


def configure_index() -> None:
    """
    Set index settings on startup — searchable and filterable attributes.
    Safe to call repeatedly (idempotent). Raises on connection failure;
    caller wraps in try/except.
    """
    client = get_client()
    index = client.index(_INDEX)
    index.update_searchable_attributes(["title", "content", "url"])
    index.update_filterable_attributes(["community_id", "is_removed", "author_id"])
    index.update_sortable_attributes(["karma", "created_at"])


# ---------------------------------------------------------------------------
# Sync operations (called via asyncio.to_thread)
# ---------------------------------------------------------------------------

def _index_post(post) -> None:
    """Upsert a post document into the search index."""
    doc = {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "url": post.url,
        "image_url": post.image_url,
        "author_id": post.author_id,
        "community_id": post.community_id,
        "karma": post.karma,
        "is_removed": post.is_removed,
        "created_at": post.created_at.isoformat() if post.created_at else None,
    }
    get_client().index(_INDEX).add_documents([doc])


def _deindex_post(post_id: int) -> None:
    """Remove a post document from the search index."""
    get_client().index(_INDEX).delete_document(post_id)


def search_posts(
    q: str,
    community_id: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """
    Run a full-text search. Removed posts are always excluded.
    Returns the raw Meilisearch response dict (keys: hits, estimatedTotalHits, …).
    """
    filters = ["is_removed = false"]
    if community_id is not None:
        filters.append(f"community_id = {community_id}")

    return get_client().index(_INDEX).search(
        q,
        {
            "filter": " AND ".join(filters),
            "limit": limit,
            "offset": offset,
        },
    )


# ---------------------------------------------------------------------------
# Async wrappers — safe to await from route handlers
# ---------------------------------------------------------------------------

async def index_post(post) -> None:
    """Index a post asynchronously. Silently ignores all errors."""
    if not settings.search_enabled:
        return
    try:
        await asyncio.to_thread(_index_post, post)
    except Exception:
        pass


async def deindex_post(post_id: int) -> None:
    """Remove a post from the index asynchronously. Silently ignores all errors."""
    if not settings.search_enabled:
        return
    try:
        await asyncio.to_thread(_deindex_post, post_id)
    except Exception:
        pass
