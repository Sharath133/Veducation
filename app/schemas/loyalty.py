"""
Loyalty API schemas
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class LoyaltyBalanceResponse(BaseModel):
    """Current loyalty balances for the authenticated user."""

    loyalty_points: int = Field(..., ge=0, description="Spendable loyalty points")
    free_duel_entry_credits: int = Field(
        ..., ge=0, description="Free duel registrations available at checkout"
    )
    points_per_free_entry: int = Field(default=50)


class LoyaltyTransactionItem(BaseModel):
    """Single ledger row."""

    id: UUID
    transaction_type: str
    points: int
    description: Optional[str] = None
    reference_id: Optional[UUID] = None
    created_at: datetime


class LoyaltyTransactionsResponse(BaseModel):
    """Paginated-style list of loyalty ledger entries."""

    transactions: List[LoyaltyTransactionItem]


class RedeemLoyaltyResponse(BaseModel):
    """Result of redeeming points for a free duel entry credit."""

    loyalty_points: int
    free_duel_entry_credits: int
    points_redeemed: int = Field(default=50)
    message: str
