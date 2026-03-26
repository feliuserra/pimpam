from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.block import Block


async def get_block(db: AsyncSession, blocker_id: int, blocked_id: int) -> Block | None:
    result = await db.execute(
        select(Block).where(
            Block.blocker_id == blocker_id, Block.blocked_id == blocked_id
        )
    )
    return result.scalar_one_or_none()


async def create_block(db: AsyncSession, blocker_id: int, blocked_id: int) -> Block:
    block = Block(blocker_id=blocker_id, blocked_id=blocked_id)
    db.add(block)
    await db.commit()
    await db.refresh(block)
    return block


async def remove_block(db: AsyncSession, blocker_id: int, blocked_id: int) -> bool:
    """Remove a block. Returns True if a block was deleted."""
    result = await db.execute(
        delete(Block).where(
            Block.blocker_id == blocker_id, Block.blocked_id == blocked_id
        )
    )
    await db.commit()
    return result.rowcount > 0


async def get_blocked_users(
    db: AsyncSession, blocker_id: int, limit: int = 100
) -> list[Block]:
    result = await db.execute(
        select(Block)
        .where(Block.blocker_id == blocker_id)
        .order_by(Block.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_blocked_user_ids(db: AsyncSession, user_id: int) -> set[int]:
    """Return the set of user IDs that user_id has blocked."""
    result = await db.execute(
        select(Block.blocked_id).where(Block.blocker_id == user_id)
    )
    return set(result.scalars().all())


async def get_blocker_ids(db: AsyncSession, user_id: int) -> set[int]:
    """Return the set of user IDs that have blocked user_id."""
    result = await db.execute(
        select(Block.blocker_id).where(Block.blocked_id == user_id)
    )
    return set(result.scalars().all())


async def is_blocked_either_direction(
    db: AsyncSession, user_a: int, user_b: int
) -> bool:
    """Check if either user has blocked the other."""
    from sqlalchemy import or_

    result = await db.execute(
        select(Block.id)
        .where(
            or_(
                (Block.blocker_id == user_a) & (Block.blocked_id == user_b),
                (Block.blocker_id == user_b) & (Block.blocked_id == user_a),
            )
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None
