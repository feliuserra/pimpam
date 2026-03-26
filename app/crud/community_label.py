from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_label import CommunityLabel
from app.schemas.community_label import LabelCreate, LabelUpdate


async def list_labels(db: AsyncSession, community_id: int) -> list[CommunityLabel]:
    result = await db.execute(
        select(CommunityLabel)
        .where(CommunityLabel.community_id == community_id)
        .order_by(CommunityLabel.position, CommunityLabel.id)
    )
    return list(result.scalars().all())


async def get_label(db: AsyncSession, label_id: int) -> CommunityLabel | None:
    result = await db.execute(
        select(CommunityLabel).where(CommunityLabel.id == label_id)
    )
    return result.scalar_one_or_none()


async def create_label(
    db: AsyncSession, community_id: int, data: LabelCreate
) -> CommunityLabel:
    # Assign position after last existing label
    result = await db.execute(
        select(CommunityLabel.position)
        .where(CommunityLabel.community_id == community_id)
        .order_by(CommunityLabel.position.desc())
        .limit(1)
    )
    last_pos = result.scalar_one_or_none()
    next_pos = (last_pos or 0) + 1

    label = CommunityLabel(
        community_id=community_id,
        name=data.name.strip(),
        color=data.color,
        description=data.description,
        position=next_pos,
    )
    db.add(label)
    await db.commit()
    await db.refresh(label)
    return label


async def update_label(
    db: AsyncSession, label: CommunityLabel, data: LabelUpdate
) -> CommunityLabel:
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "name" and value is not None:
            value = value.strip()
        setattr(label, field, value)
    await db.commit()
    await db.refresh(label)
    return label


async def delete_label(db: AsyncSession, label: CommunityLabel) -> None:
    await db.delete(label)
    await db.commit()


async def reorder_labels(
    db: AsyncSession, community_id: int, ordered_ids: list[int]
) -> list[CommunityLabel]:
    labels = await list_labels(db, community_id)
    label_map = {lbl.id: lbl for lbl in labels}

    for position, label_id in enumerate(ordered_ids):
        if label_id in label_map:
            label_map[label_id].position = position

    await db.commit()
    return await list_labels(db, community_id)
