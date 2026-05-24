"""
Rewards API schemas
"""
from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field


class RewardHistoryItem(BaseModel):
    """Single rewards_history row for the client table."""

    id: UUID
    duel_date: str = Field(description="Daily duel calendar date (YYYY-MM-DD)")
    rank: int
    reward_amount: str = Field(description="Payout amount as decimal string")
    payment_status: str
    created_at: datetime
    processed_at: datetime | None = None

    class Config:
        from_attributes = True


class RewardHistoryResponse(BaseModel):
    items: List[RewardHistoryItem]
