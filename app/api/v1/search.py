"""
Search endpoint — full-text search over posts, users, and communities via Meilisearch.

GET /api/v1/search
  ?q=<query>                  required — search terms
  ?type=post|user|community   optional — limit to one kind (default: all three)
  ?community=<name>           optional — restrict post results to a single community
  ?limit=20                   results per page (max 100)
  ?offset=0                   pagination offset

Returns 503 if search is disabled or Meilisearch is unreachable.
"""
import asyncio
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.dependencies import DBSession
from app.core.search import search_communities, search_posts, search_users
from app.crud.community import get_community_by_name

router = APIRouter(prefix="/search", tags=["search"])


class PostHit(BaseModel):
    type: Literal["post"] = "post"
    id: int
    title: str
    content: str | None
    url: str | None
    image_url: str | None
    author_id: int
    community_id: int | None
    karma: int
    created_at: datetime | None


class UserHit(BaseModel):
    type: Literal["user"] = "user"
    id: int
    username: str
    display_name: str | None
    bio: str | None
    avatar_url: str | None
    karma: int


class CommunityHit(BaseModel):
    type: Literal["community"] = "community"
    id: int
    name: str
    description: str | None
    member_count: int
    created_at: datetime | None


class SearchResponse(BaseModel):
    hits: list[PostHit | UserHit | CommunityHit]
    total: int
    query: str


@router.get("", response_model=SearchResponse)
async def search(
    db: DBSession,
    q: str = Query(..., min_length=1, description="Search query"),
    type: Literal["post", "user", "community"] | None = Query(
        None, description="Restrict to one result type. Omit to search all."
    ),
    community: str | None = Query(None, description="Restrict post results to this community name"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    Full-text search over posts, users, and communities.

    Pass ``type`` to narrow results to a single kind. Results are ranked by
    relevance (Meilisearch default). Removed posts are never returned.
    """
    if not settings.search_enabled:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search is not configured on this server",
        )

    community_id: int | None = None
    if community:
        community_obj = await get_community_by_name(db, community)
        if community_obj is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Community not found")
        community_id = community_obj.id

    hits: list[PostHit | UserHit | CommunityHit] = []
    total = 0

    try:
        if type in (None, "post"):
            result = await asyncio.to_thread(search_posts, q, community_id, limit, offset)
            for h in result.get("hits", []):
                hits.append(PostHit(**h))
            total += result.get("estimatedTotalHits", len(hits))

        if type in (None, "user"):
            result = await asyncio.to_thread(search_users, q, limit, offset)
            for h in result.get("hits", []):
                hits.append(UserHit(**h))
            total += result.get("estimatedTotalHits", 0)

        if type in (None, "community"):
            result = await asyncio.to_thread(search_communities, q, limit, offset)
            for h in result.get("hits", []):
                hits.append(CommunityHit(**h))
            total += result.get("estimatedTotalHits", 0)

    except Exception:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search service unavailable",
        )

    return SearchResponse(hits=hits, total=total, query=q)
