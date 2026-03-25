import uuid
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import get_user_roles
from app.models.workflow import WorkflowState, WorkflowTransition
from app.services.audit_service import audit_service
from app.services.event_bus import event_bus
from app.schemas.workflow import TransitionOption


class WorkflowEngine:
    async def get_states(self, db: AsyncSession, tenant_id: uuid.UUID) -> List[WorkflowState]:
        result = await db.execute(
            select(WorkflowState)
            .where(WorkflowState.tenant_id == tenant_id)
            .order_by(WorkflowState.display_order)
        )
        return list(result.scalars().all())

    async def get_initial_state(self, db: AsyncSession, tenant_id: uuid.UUID) -> str:
        result = await db.execute(
            select(WorkflowState)
            .where(WorkflowState.tenant_id == tenant_id, WorkflowState.is_initial == True)
        )
        state = result.scalar_one_or_none()
        if not state:
            return "draft"
        return state.slug

    async def get_valid_transitions(
        self, db: AsyncSession, current_state: str, tenant_id: uuid.UUID, user
    ) -> List[TransitionOption]:
        user_roles = get_user_roles(user)

        result = await db.execute(
            select(WorkflowTransition)
            .where(
                WorkflowTransition.tenant_id == tenant_id,
                WorkflowTransition.from_state == current_state,
            )
        )
        transitions = result.scalars().all()

        valid = []
        for t in transitions:
            if any(role in t.allowed_roles for role in user_roles):
                state_result = await db.execute(
                    select(WorkflowState).where(
                        WorkflowState.tenant_id == tenant_id,
                        WorkflowState.slug == t.to_state,
                    )
                )
                state_obj = state_result.scalar_one_or_none()
                state_name = state_obj.name if state_obj else t.to_state
                valid.append(TransitionOption(to_state=t.to_state, state_name=state_name))
        return valid

    async def transition(self, db: AsyncSession, issue, target_state: str, user):
        valid = await self.get_valid_transitions(db, issue.status, issue.tenant_id, user)
        valid_slugs = [v.to_state for v in valid]

        if target_state not in valid_slugs:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Transition from '{issue.status}' to '{target_state}' is not allowed for your role",
            )

        old_status = issue.status
        issue.status = target_state

        if target_state in ("closed", "approved"):
            from datetime import datetime, timezone
            issue.resolved_at = datetime.now(timezone.utc)

        await audit_service.log(
            db=db,
            entity_type="issue",
            entity_id=issue.id,
            action="status_change",
            user_id=user.id,
            tenant_id=issue.tenant_id,
            field_name="status",
            old_value=old_status,
            new_value=target_state,
        )

        await db.flush()

        await event_bus.emit("IssueUpdated", {
            "issue_id": str(issue.id),
            "tenant_id": str(issue.tenant_id),
            "old_status": old_status,
            "new_status": target_state,
            "user_id": str(user.id),
        })

        return issue


workflow_engine = WorkflowEngine()
