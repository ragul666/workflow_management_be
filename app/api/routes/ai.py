import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.issue import Issue
from app.models.ai_summary import AISummary
from app.models.user import User
from app.schemas.ai_summary import AISummaryRequest, AISummaryResponse, AISummaryListResponse
from app.services.ai_service import ai_service

router = APIRouter(prefix="/ai", tags=["AI Integration"])


@router.post("/generate-summary", response_model=AISummaryResponse)
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

    summary = await ai_service.generate_summary(
        db=db,
        issue_id=issue.id,
        issue_title=issue.title,
        issue_description=issue.description,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )

    return AISummaryResponse.model_validate(summary)


@router.get("/summaries/{issue_id}", response_model=AISummaryListResponse)
async def get_summaries(
    issue_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AISummary)
        .where(
            AISummary.issue_id == issue_id,
            AISummary.tenant_id == current_user.tenant_id,
        )
        .order_by(AISummary.version.desc())
    )
    summaries = result.scalars().all()
    return AISummaryListResponse(items=[AISummaryResponse.model_validate(s) for s in summaries])
