import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditService:
    @staticmethod
    async def log(
        db: AsyncSession,
        entity_type: str,
        entity_id: uuid.UUID,
        action: str,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        field_name: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        issue_id: Optional[uuid.UUID] = None,
    ):
        entry = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            issue_id=issue_id or (entity_id if entity_type == "issue" else None),
            action=action,
            field_name=field_name,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
            user_id=user_id,
            tenant_id=tenant_id,
        )
        db.add(entry)
        await db.flush()
        return entry


audit_service = AuditService()
