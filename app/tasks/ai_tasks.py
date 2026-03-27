import asyncio
import uuid

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, func

from app.core.config import settings
from app.models.ai_summary import AISummary
from app.services.ai_service import ai_service
from app.tasks.celery_app import celery_app


async def _generate_summary_async(
    issue_id: str,
    issue_title: str,
    issue_description: str,
    user_id: str,
    tenant_id: str,
) -> dict:
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        summary = await ai_service.generate_summary(
            db=db,
            issue_id=uuid.UUID(issue_id),
            issue_title=issue_title,
            issue_description=issue_description,
            user_id=uuid.UUID(user_id),
            tenant_id=uuid.UUID(tenant_id),
        )
        await db.commit()
        return {
            "id": str(summary.id),
            "issue_id": str(summary.issue_id),
            "version": summary.version,
            "content": summary.content,
            "model_used": summary.model_used,
            "generated_by": str(summary.generated_by),
            "created_at": summary.created_at.isoformat(),
        }

    await engine.dispose()


@celery_app.task(name="app.tasks.ai_tasks.generate_ai_summary")
def generate_ai_summary(
    issue_id: str,
    issue_title: str,
    issue_description: str,
    user_id: str,
    tenant_id: str,
) -> dict:
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(
            _generate_summary_async(issue_id, issue_title, issue_description, user_id, tenant_id)
        )
    finally:
        loop.close()
