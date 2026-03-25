import asyncio
from datetime import datetime, timezone

from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings
from app.models.issue import Issue
from app.tasks.celery_app import celery_app


async def _check_overdue():
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        now = datetime.now(timezone.utc)
        stmt = (
            update(Issue)
            .where(
                and_(
                    Issue.due_date != None,
                    Issue.due_date < now,
                    Issue.is_overdue == False,
                    Issue.resolved_at == None,
                )
            )
            .values(is_overdue=True)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    await engine.dispose()


@celery_app.task(name="app.tasks.sla_tasks.check_sla_breaches")
def check_sla_breaches():
    loop = asyncio.new_event_loop()
    try:
        count = loop.run_until_complete(_check_overdue())
        return {"marked_overdue": count}
    finally:
        loop.close()
