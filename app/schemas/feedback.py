"""
Feedback / suggestion schemas
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class FeedbackCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    body: str = Field(..., min_length=10, max_length=8000)
    category: str = Field(
        default="suggestion",
        pattern="^(suggestion|bug|feature_request|other)$",
    )

    @field_validator("title", "body")
    @classmethod
    def strip_not_empty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("must not be empty or whitespace only")
        return s


class FeedbackOut(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    body: str
    category: str
    created_at: datetime

    class Config:
        from_attributes = True
