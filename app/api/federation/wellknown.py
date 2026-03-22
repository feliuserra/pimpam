"""
Well-known endpoints required for ActivityPub federation discovery.
  GET /.well-known/webfinger  — resolves acct:user@domain to an AP actor URL
  GET /.well-known/nodeinfo   — points to the NodeInfo document
  GET /nodeinfo/2.1           — server capabilities and usage stats
"""
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from app.core.config import settings
from app.core.dependencies import DBSession
from app.crud.user import get_user_by_username
from app.federation.actor import actor_id
from app.federation.constants import NODEINFO_SCHEMA
from app.models.user import User

router = APIRouter(tags=["federation"])


@router.get("/.well-known/webfinger")
async def webfinger(
    db: DBSession,
    resource: str = Query(..., description="acct:username@domain"),
):
    """
    Actor discovery. Allows remote servers to resolve acct:user@domain
    to this server's AP actor URL.
    """
    if not resource.startswith("acct:"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="resource must start with acct:")

    acct = resource[len("acct:"):]
    if "@" not in acct:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Malformed acct URI")

    username, domain = acct.rsplit("@", 1)
    if domain != settings.domain:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found on this server")

    user = await get_user_by_username(db, username)
    if user is None or user.is_remote:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

    ap_actor_url = actor_id(username)
    body = {
        "subject": resource,
        "aliases": [ap_actor_url, f"https://{settings.domain}/@{username}"],
        "links": [
            {"rel": "self", "type": "application/activity+json", "href": ap_actor_url},
            {"rel": "http://webfinger.net/rel/profile-page", "type": "text/html", "href": f"https://{settings.domain}/@{username}"},
        ],
    }
    return JSONResponse(content=body, media_type="application/jrd+json")


@router.get("/.well-known/nodeinfo")
async def nodeinfo_discovery():
    """Points remote servers to the NodeInfo document."""
    return {"links": [{"rel": NODEINFO_SCHEMA, "href": f"https://{settings.domain}/nodeinfo/2.1"}]}


@router.get("/nodeinfo/2.1")
async def nodeinfo(db: DBSession):
    """NodeInfo 2.1 — server capabilities and usage statistics."""
    result = await db.execute(
        select(func.count()).select_from(User).where(User.is_remote == False, User.is_active == True)  # noqa: E712
    )
    body = {
        "version": "2.1",
        "software": {"name": "pimpam", "version": settings.app_version},
        "protocols": ["activitypub"],
        "usage": {"users": {"total": result.scalar_one()}},
        "openRegistrations": True,
    }
    return JSONResponse(content=body, media_type=f"application/json; profile={NODEINFO_SCHEMA}")
