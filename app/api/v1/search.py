"""
Search endpoint — full-text search over posts via Meilisearch.

GET /api/v1/search
  ?q=<query>            required — search terms
  ?community=<name>     optional — restrict to a single community
  ?limit=20             results per page (max 100)
  ?offset=0             pagination offset

Results come directly from the Meilisearch index so no extra DB round-trip is
needed. Removed posts are always excluded (filtered server-side).

Returns 503 if search is disabled or Meilisearch is unreachable.
"""
import asyncio
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.dependencies import DBSession
from app.core.search import search_posts
from app.crud.community import get_community_by_name

router = APIRouter(prefix="/search", tags=["search"])


class SearchHit(BaseModel):
    id: int
    title: str
    content: str | None
    url: str | None
    image_url: str | None
    author_id: int
    community_id: int | None
    karma: int
    created_at: datetime | None


class SearchResponse(BaseModel):
    hits: list[SearchHit]
    total: int
    query: str


@router.get("", response_model=SearchResponse)
async def search(
    db: DBSession,
    q: str = Query(..., min_length=1, description="Search query"),
    community: str | None = Query(None, description="Restrict results to this community name"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    Full-text search over post titles and content.

    Results are ranked by relevance (Meilisearch default). Removed posts are
    never returned. Pass ``community`` to scope the search to a single community.
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

    try:
        result = await asyncio.to_thread(search_posts, q, community_id, limit, offset)
    except Exception:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search service unavailable",
        )

    hits = [SearchHit(**hit) for hit in result.get("hits", [])]
    total = result.get("estimatedTotalHits", len(hits))

    return SearchResponse(hits=hits, total=total, query=q)
