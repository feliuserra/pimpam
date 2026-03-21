from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.remote_actor import RemoteActor
from app.schemas.federation import RemoteActorCreate


async def get_remote_actor_by_ap_id(db: AsyncSession, ap_id: str) -> RemoteActor | None:
    result = await db.execute(select(RemoteActor).where(RemoteActor.ap_id == ap_id))
    return result.scalar_one_or_none()


async def upsert_remote_actor(db: AsyncSession, data: RemoteActorCreate) -> RemoteActor:
    """Insert or update a remote actor cache entry on ap_id conflict."""
    existing = await get_remote_actor_by_ap_id(db, data.ap_id)
    if existing:
        for field, value in data.model_dump().items():
            setattr(existing, field, value)
        existing.fetched_at = datetime.now(timezone.utc)
    else:
        existing = RemoteActor(**data.model_dump(), fetched_at=datetime.now(timezone.utc))
        db.add(existing)
    await db.commit()
    await db.refresh(existing)
    return existing


async def get_remote_actors_by_domain(db: AsyncSession, domain: str) -> list[RemoteActor]:
    result = await db.execute(select(RemoteActor).where(RemoteActor.domain == domain))
    return list(result.scalars().all())
