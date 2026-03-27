import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.issue import Issue
from app.models.ai_summary import AISummary
from app.models.user import User
from app.schemas.ai_summary import AISummaryRequest, AISummaryResponse, AISummaryListResponse
from app.services.ai_service import ai_service

router = APIRouter(prefix="/ai", tags=["AI Integration"])


@router.post("/generate-summary")
async def generate_summary(
    body: AISummaryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Issue).where(
            Issue.id == body.issue_id,
            Issue.tenant_id == current_user.tenant_id,
        )
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    from app.tasks.ai_tasks import generate_ai_summary
    task = generate_ai_summary.delay(
        issue_id=str(issue.id),
        issue_title=issue.title,
        issue_description=issue.description,
        user_id=str(current_user.id),
        tenant_id=str(current_user.tenant_id),
    )

    return {"task_id": task.id, "status": "processing"}


@router.get("/task-status/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    from app.tasks.celery_app import celery_app
    result = celery_app.AsyncResult(task_id)
    if result.ready():
        return {"status": "completed", "result": result.result}
    return {"status": "processing"}


@router.get("/summaries/{issue_id}", response_model=AISummaryListResponse)
async def get_summaries(
    issue_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count_result = await db.execute(
        select(func.count(AISummary.id))
        .where(
            AISummary.issue_id == issue_id,
            AISummary.tenant_id == current_user.tenant_id,
        )
    )
    total = count_result.scalar()

    offset = (page - 1) * page_size
    result = await db.execute(
        select(AISummary)
        .where(
            AISummary.issue_id == issue_id,
            AISummary.tenant_id == current_user.tenant_id,
        )
        .order_by(AISummary.version.desc())
        .offset(offset)
        .limit(page_size)
    )
    summaries = result.scalars().all()
    return AISummaryListResponse(
        items=[AISummaryResponse.model_validate(s) for s in summaries],
        total=total,
        page=page,
        page_size=page_size,
    )
