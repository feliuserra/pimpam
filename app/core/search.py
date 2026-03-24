"""
Meilisearch integration — full-text search over posts, users, and communities.

Works with any Meilisearch v1.x instance. In development the server runs via
docker-compose (port 7700) with no auth. In production, set SEARCH_API_KEY to
your master key.

All indexing is fire-and-forget: if Meilisearch is unavailable, create/edit/
delete operations succeed normally and the search index is simply out of sync
until the service recovers.
"""
import asyncio

import meilisearch

from app.core.config import settings

_POSTS_INDEX = "posts"
_USERS_INDEX = "users"
_COMMUNITIES_INDEX = "communities"


def get_client() -> meilisearch.Client:
    return meilisearch.Client(settings.search_url, settings.search_api_key or None)


def configure_index() -> None:
    """
    Set index settings on startup — searchable and filterable attributes.
    Safe to call repeatedly (idempotent). Raises on connection failure;
    caller wraps in try/except.
    """
    client = get_client()

    posts = client.index(_POSTS_INDEX)
    posts.update_searchable_attributes(["title", "content", "url"])
    posts.update_filterable_attributes(["community_id", "is_removed", "author_id"])
    posts.update_sortable_attributes(["karma", "created_at"])

    users = client.index(_USERS_INDEX)
    users.update_searchable_attributes(["username", "display_name", "bio"])
    users.update_filterable_attributes(["is_active", "is_remote"])

    communities = client.index(_COMMUNITIES_INDEX)
    communities.update_searchable_attributes(["name", "description"])
    communities.update_sortable_attributes(["member_count", "created_at"])


# ---------------------------------------------------------------------------
# Posts — sync operations (called via asyncio.to_thread)
# ---------------------------------------------------------------------------

def _index_post(post) -> None:
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
    get_client().index(_POSTS_INDEX).add_documents([doc])


def _deindex_post(post_id: int) -> None:
    get_client().index(_POSTS_INDEX).delete_document(post_id)


def search_posts(
    q: str,
    community_id: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Run a full-text search over posts. Removed posts are always excluded."""
    filters = ["is_removed = false"]
    if community_id is not None:
        filters.append(f"community_id = {community_id}")
    return get_client().index(_POSTS_INDEX).search(
        q, {"filter": " AND ".join(filters), "limit": limit, "offset": offset}
    )


# ---------------------------------------------------------------------------
# Users — sync operations
# ---------------------------------------------------------------------------

def _index_user(user) -> None:
    doc = {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "karma": user.karma,
        "is_active": user.is_active,
        "is_remote": user.is_remote,
    }
    get_client().index(_USERS_INDEX).add_documents([doc])


def _deindex_user(user_id: int) -> None:
    get_client().index(_USERS_INDEX).delete_document(user_id)


def search_users(q: str, limit: int = 20, offset: int = 0) -> dict:
    """Search local, active users by username, display name, or bio."""
    return get_client().index(_USERS_INDEX).search(
        q,
        {
            "filter": "is_active = true AND is_remote = false",
            "limit": limit,
            "offset": offset,
        },
    )


# ---------------------------------------------------------------------------
# Communities — sync operations
# ---------------------------------------------------------------------------

def _index_community(community) -> None:
    doc = {
        "id": community.id,
        "name": community.name,
        "description": community.description,
        "member_count": community.member_count,
        "created_at": community.created_at.isoformat() if community.created_at else None,
    }
    get_client().index(_COMMUNITIES_INDEX).add_documents([doc])


def _deindex_community(community_id: int) -> None:
    get_client().index(_COMMUNITIES_INDEX).delete_document(community_id)


def search_communities(q: str, limit: int = 20, offset: int = 0) -> dict:
    """Search communities by name or description."""
    return get_client().index(_COMMUNITIES_INDEX).search(
        q, {"limit": limit, "offset": offset}
    )


# ---------------------------------------------------------------------------
# Async wrappers — safe to await from route handlers
# ---------------------------------------------------------------------------

async def index_post(post) -> None:
    if not settings.search_enabled:
        return
    try:
        await asyncio.to_thread(_index_post, post)
    except Exception:
        pass


async def deindex_post(post_id: int) -> None:
    if not settings.search_enabled:
        return
    try:
        await asyncio.to_thread(_deindex_post, post_id)
    except Exception:
        pass


async def index_user(user) -> None:
    if not settings.search_enabled:
        return
    try:
        await asyncio.to_thread(_index_user, user)
    except Exception:
        pass


async def deindex_user(user_id: int) -> None:
    if not settings.search_enabled:
        return
    try:
        await asyncio.to_thread(_deindex_user, user_id)
    except Exception:
        pass


async def index_community(community) -> None:
    if not settings.search_enabled:
        return
    try:
        await asyncio.to_thread(_index_community, community)
    except Exception:
        pass


async def deindex_community(community_id: int) -> None:
    if not settings.search_enabled:
        return
    try:
        await asyncio.to_thread(_deindex_community, community_id)
    except Exception:
        pass
