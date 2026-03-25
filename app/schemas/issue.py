import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class IssueCreate(BaseModel):
    title: str
    description: str
    category: str = "compliance"
    priority: str = "medium"
    due_date: Optional[datetime] = None
    assigned_to: Optional[uuid.UUID] = None


class IssueUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    assigned_to: Optional[uuid.UUID] = None


class IssueTransition(BaseModel):
    target_state: str


class IssueResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    category: str
    priority: str
    status: str
    due_date: Optional[datetime]
    resolved_at: Optional[datetime]
    is_overdue: bool
    tenant_id: uuid.UUID
    created_by: uuid.UUID
    assigned_to: Optional[uuid.UUID]
    creator_name: Optional[str] = None
    assignee_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IssueListResponse(BaseModel):
    items: List[IssueResponse]
    total: int
    page: int
    page_size: int
