import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    action: str
    field_name: Optional[str]
    old_value: Optional[str]
    new_value: Optional[str]
    user_id: uuid.UUID
    timestamp: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
