import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.rbac import has_permission
from app.models.issue import Issue
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.issue import IssueCreate, IssueUpdate, IssueTransition, IssueResponse, IssueListResponse
from app.schemas.audit import AuditLogResponse, AuditLogListResponse
from app.services.audit_service import audit_service
from app.services.workflow_engine import workflow_engine
from app.services.sla_service import sla_service
from app.services.event_bus import event_bus

router = APIRouter(prefix="/issues", tags=["Issues"])


def _build_issue_response(issue: Issue) -> IssueResponse:
    """Shared helper to build IssueResponse from Issue model."""
    return IssueResponse(
        id=issue.id,
        title=issue.title,
        description=issue.description,
        category=issue.category,
        priority=issue.priority,
        status=issue.status,
        due_date=issue.due_date,
        resolved_at=issue.resolved_at,
        is_overdue=issue.is_overdue,
        tenant_id=issue.tenant_id,
        created_by=issue.created_by,
        assigned_to=issue.assigned_to,
        creator_name=issue.creator.full_name if issue.creator else None,
        assignee_name=issue.assignee.full_name if issue.assignee else None,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
    )


@router.get("", response_model=IssueListResponse)
async def list_issues(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = None,
    priority: Optional[str] = None,
    is_overdue: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Issue).where(Issue.tenant_id == current_user.tenant_id)
    count_query = select(func.count(Issue.id)).where(Issue.tenant_id == current_user.tenant_id)

    if status_filter:
        query = query.where(Issue.status == status_filter)
        count_query = count_query.where(Issue.status == status_filter)
    if category:
        query = query.where(Issue.category == category)
        count_query = count_query.where(Issue.category == category)
    if priority:
        query = query.where(Issue.priority == priority)
        count_query = count_query.where(Issue.priority == priority)
    if is_overdue is not None:
        query = query.where(Issue.is_overdue == is_overdue)
        count_query = count_query.where(Issue.is_overdue == is_overdue)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    offset = (page - 1) * page_size
    query = (
        query
        .options(
            selectinload(Issue.creator),
            selectinload(Issue.assignee),
        )
        .order_by(Issue.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    issues = result.scalars().all()

    items = [_build_issue_response(issue) for issue in issues]

    return IssueListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=IssueResponse, status_code=status.HTTP_201_CREATED)
async def create_issue(
    body: IssueCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    initial_state = await workflow_engine.get_initial_state(db, current_user.tenant_id)

    issue = Issue(
        title=body.title,
        description=body.description,
        category=body.category,
        priority=body.priority,
        status=initial_state,
        due_date=body.due_date,
        assigned_to=body.assigned_to,
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
    )
    db.add(issue)
    await db.flush()

    await audit_service.log(
        db=db,
        entity_type="issue",
        entity_id=issue.id,
        action="created",
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        field_name="status",
        new_value=initial_state,
    )

    await event_bus.emit("IssueCreated", {
        "issue_id": str(issue.id),
        "tenant_id": str(current_user.tenant_id),
        "title": issue.title,
        "status": issue.status,
    })

    await db.refresh(issue, ["creator", "assignee"])
    return _build_issue_response(issue)


@router.get("/{issue_id}", response_model=IssueResponse)
async def get_issue(
    issue_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Issue)
        .options(
            selectinload(Issue.creator),
            selectinload(Issue.assignee),
        )
        .where(Issue.id == issue_id, Issue.tenant_id == current_user.tenant_id)
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    return _build_issue_response(issue)


@router.patch("/{issue_id}", response_model=IssueResponse)
async def update_issue(
    issue_id: uuid.UUID,
    body: IssueUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Issue).where(Issue.id == issue_id, Issue.tenant_id == current_user.tenant_id)
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        old_value = getattr(issue, field)
        if old_value != value:
            await audit_service.log(
                db=db,
                entity_type="issue",
                entity_id=issue.id,
                action="updated",
                user_id=current_user.id,
                tenant_id=current_user.tenant_id,
                field_name=field,
                old_value=str(old_value),
                new_value=str(value),
            )
            setattr(issue, field, value)

    await db.flush()

    await event_bus.emit("IssueUpdated", {
        "issue_id": str(issue.id),
        "tenant_id": str(current_user.tenant_id),
    })

    await db.refresh(issue, ["creator", "assignee"])
    return _build_issue_response(issue)


@router.post("/{issue_id}/transition", response_model=IssueResponse)
async def transition_issue(
    issue_id: uuid.UUID,
    body: IssueTransition,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Issue).where(Issue.id == issue_id, Issue.tenant_id == current_user.tenant_id)
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    issue = await workflow_engine.transition(db, issue, body.target_state, current_user)
    await db.flush()

    creator = await db.get(User, issue.created_by)
    assignee = await db.get(User, issue.assigned_to) if issue.assigned_to else None

    return IssueResponse(
        id=issue.id,
        title=issue.title,
        description=issue.description,
        category=issue.category,
        priority=issue.priority,
        status=issue.status,
        due_date=issue.due_date,
        resolved_at=issue.resolved_at,
        is_overdue=issue.is_overdue,
        tenant_id=issue.tenant_id,
        created_by=issue.created_by,
        assigned_to=issue.assigned_to,
        creator_name=creator.full_name if creator else None,
        assignee_name=assignee.full_name if assignee else None,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
    )


@router.get("/{issue_id}/transitions")
async def get_transitions(
    issue_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Issue).where(Issue.id == issue_id, Issue.tenant_id == current_user.tenant_id)
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    transitions = await workflow_engine.get_valid_transitions(db, issue.status, current_user.tenant_id, current_user)
    return transitions


@router.get("/{issue_id}/audit", response_model=AuditLogListResponse)
async def get_issue_audit(
    issue_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count_result = await db.execute(
        select(func.count(AuditLog.id))
        .where(AuditLog.issue_id == issue_id, AuditLog.tenant_id == current_user.tenant_id)
    )
    total = count_result.scalar()

    offset = (page - 1) * page_size
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.issue_id == issue_id, AuditLog.tenant_id == current_user.tenant_id)
        .order_by(AuditLog.timestamp.desc())
        .offset(offset)
        .limit(page_size)
    )
    logs = result.scalars().all()
    items = [AuditLogResponse.model_validate(log) for log in logs]
    return AuditLogListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{issue_id}/sla")
async def get_issue_sla(
    issue_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Issue).where(Issue.id == issue_id, Issue.tenant_id == current_user.tenant_id)
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    return sla_service.get_sla_remaining(issue.due_date)
