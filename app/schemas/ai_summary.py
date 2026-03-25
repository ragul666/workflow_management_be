import uuid
from datetime import datetime
from typing import List

from pydantic import BaseModel


class AISummaryRequest(BaseModel):
    issue_id: uuid.UUID


class AISummaryResponse(BaseModel):
    id: uuid.UUID
    issue_id: uuid.UUID
    version: int
    content: str
    model_used: str
    generated_by: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class AISummaryListResponse(BaseModel):
    items: List[AISummaryResponse]
