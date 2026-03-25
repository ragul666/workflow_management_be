import uuid
from typing import List, Optional

from pydantic import BaseModel


class WorkflowStateCreate(BaseModel):
    name: str
    slug: str
    display_order: int = 0
    is_initial: bool = False
    is_terminal: bool = False


class WorkflowStateResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    display_order: int
    is_initial: bool
    is_terminal: bool
    tenant_id: uuid.UUID

    class Config:
        from_attributes = True


class WorkflowTransitionCreate(BaseModel):
    from_state: str
    to_state: str
    allowed_roles: List[str]


class WorkflowTransitionResponse(BaseModel):
    id: uuid.UUID
    from_state: str
    to_state: str
    allowed_roles: List[str]
    tenant_id: uuid.UUID

    class Config:
        from_attributes = True


class TransitionOption(BaseModel):
    to_state: str
    state_name: str
