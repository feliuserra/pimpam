from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report


async def get_report(
    db: AsyncSession, reporter_id: int, content_type: str, content_id: int
) -> Report | None:
    result = await db.execute(
        select(Report).where(
            Report.reporter_id == reporter_id,
            Report.content_type == content_type,
            Report.content_id == content_id,
        )
    )
    return result.scalar_one_or_none()


async def create_report(
    db: AsyncSession,
    reporter_id: int,
    content_type: str,
    content_id: int,
    reason: str,
) -> Report:
    report = Report(
        reporter_id=reporter_id,
        content_type=content_type,
        content_id=content_id,
        reason=reason,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report
