import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.user import User
from app.models.workflow import WorkflowState, WorkflowTransition
from app.schemas.workflow import (
    WorkflowStateCreate,
    WorkflowStateResponse,
    WorkflowTransitionCreate,
    WorkflowTransitionResponse,
)

router = APIRouter(prefix="/workflow", tags=["Workflow Configuration"])


@router.get("/states", response_model=list[WorkflowStateResponse])
async def list_states(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(WorkflowState)
        .where(WorkflowState.tenant_id == current_user.tenant_id)
        .order_by(WorkflowState.display_order)
    )
    return [WorkflowStateResponse.model_validate(s) for s in result.scalars().all()]


@router.post("/states", response_model=WorkflowStateResponse, status_code=status.HTTP_201_CREATED)
async def create_state(
    body: WorkflowStateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    existing = await db.execute(
        select(WorkflowState).where(
            WorkflowState.tenant_id == current_user.tenant_id,
            WorkflowState.slug == body.slug,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="State slug already exists")

    state = WorkflowState(
        name=body.name,
        slug=body.slug,
        display_order=body.display_order,
        is_initial=body.is_initial,
        is_terminal=body.is_terminal,
        tenant_id=current_user.tenant_id,
    )
    db.add(state)
    await db.flush()
    return WorkflowStateResponse.model_validate(state)


@router.put("/states/{state_id}", response_model=WorkflowStateResponse)
async def update_state(
    state_id: uuid.UUID,
    body: WorkflowStateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(WorkflowState).where(
            WorkflowState.id == state_id,
            WorkflowState.tenant_id == current_user.tenant_id,
        )
    )
    state = result.scalar_one_or_none()
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="State not found")

    state.name = body.name
    state.slug = body.slug
    state.display_order = body.display_order
    state.is_initial = body.is_initial
    state.is_terminal = body.is_terminal
    await db.flush()
    return WorkflowStateResponse.model_validate(state)


@router.delete("/states/{state_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_state(
    state_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(WorkflowState).where(
            WorkflowState.id == state_id,
            WorkflowState.tenant_id == current_user.tenant_id,
        )
    )
    state = result.scalar_one_or_none()
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="State not found")
    await db.delete(state)
    await db.flush()


@router.get("/transitions", response_model=list[WorkflowTransitionResponse])
async def list_transitions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(WorkflowTransition).where(WorkflowTransition.tenant_id == current_user.tenant_id)
    )
    return [WorkflowTransitionResponse.model_validate(t) for t in result.scalars().all()]


@router.post("/transitions", response_model=WorkflowTransitionResponse, status_code=status.HTTP_201_CREATED)
async def create_transition(
    body: WorkflowTransitionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    transition = WorkflowTransition(
        from_state=body.from_state,
        to_state=body.to_state,
        allowed_roles=body.allowed_roles,
        tenant_id=current_user.tenant_id,
    )
    db.add(transition)
    await db.flush()
    return WorkflowTransitionResponse.model_validate(transition)


@router.put("/transitions/{transition_id}", response_model=WorkflowTransitionResponse)
async def update_transition(
    transition_id: uuid.UUID,
    body: WorkflowTransitionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(WorkflowTransition).where(
            WorkflowTransition.id == transition_id,
            WorkflowTransition.tenant_id == current_user.tenant_id,
        )
    )
    transition = result.scalar_one_or_none()
    if not transition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transition not found")

    transition.from_state = body.from_state
    transition.to_state = body.to_state
    transition.allowed_roles = body.allowed_roles
    await db.flush()
    return WorkflowTransitionResponse.model_validate(transition)


@router.delete("/transitions/{transition_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transition(
    transition_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(WorkflowTransition).where(
            WorkflowTransition.id == transition_id,
            WorkflowTransition.tenant_id == current_user.tenant_id,
        )
    )
    transition = result.scalar_one_or_none()
    if not transition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transition not found")
    await db.delete(transition)
    await db.flush()
