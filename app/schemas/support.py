"""
Support ticket schemas
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SupportTicketCreate(BaseModel):
    subject: str = Field(..., min_length=3, max_length=200)
    body: str = Field(..., min_length=10, max_length=8000)

    @field_validator("subject", "body")
    @classmethod
    def strip_not_empty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("must not be empty or whitespace only")
        return s


class SupportTicketOut(BaseModel):
    id: UUID
    user_id: UUID
    subject: str
    body: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SupportTicketStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(open|in_progress|resolved|closed)$")
