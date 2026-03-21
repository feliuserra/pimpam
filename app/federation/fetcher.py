"""
Fetch and cache remote ActivityPub actor documents.
The cache lives in the remote_actors table with a TTL-based invalidation.
"""
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud.remote_actor import get_remote_actor_by_ap_id, upsert_remote_actor
from app.schemas.federation import RemoteActorCreate


class FederationFetchError(Exception):
    """Raised when a remote AP document cannot be fetched."""


async def fetch_remote_actor(ap_id: str, db: AsyncSession) -> dict:
    """
    Return a remote actor document, using the DB cache when fresh.
    Raises FederationFetchError if the actor cannot be retrieved.
    """
    cached = await get_remote_actor_by_ap_id(db, ap_id)
    ttl = timedelta(seconds=settings.remote_actor_cache_ttl_seconds)
    if cached and datetime.now(timezone.utc) - cached.fetched_at < ttl:
        return json.loads(cached.actor_json)

    doc = await _fetch(ap_id)
    await upsert_remote_actor(
        db,
        RemoteActorCreate(
            ap_id=ap_id,
            username=doc.get("preferredUsername", ""),
            domain=urlparse(ap_id).netloc,
            inbox_url=doc.get("inbox", ""),
            shared_inbox_url=doc.get("endpoints", {}).get("sharedInbox"),
            public_key_pem=doc.get("publicKey", {}).get("publicKeyPem", ""),
            actor_json=json.dumps(doc),
        ),
    )
    return doc


async def _fetch(url: str) -> dict:
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=15.0, write=5.0, pool=5.0)) as client:
        try:
            resp = await client.get(url, headers={"Accept": "application/activity+json"})
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise FederationFetchError(f"Could not fetch {url}: {exc}") from exc


