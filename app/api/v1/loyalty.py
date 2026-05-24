"""
Loyalty Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.loyalty import (
    LoyaltyBalanceResponse,
    LoyaltyTransactionItem,
    LoyaltyTransactionsResponse,
    RedeemLoyaltyResponse,
)
from app.services.loyalty_service import LoyaltyService

router = APIRouter()


@router.get("/points", response_model=LoyaltyBalanceResponse)
async def get_loyalty_points(current_user: User = Depends(get_current_user)):
    """Return loyalty point balance and free duel entry credits."""
    return LoyaltyService.build_balance_payload(current_user)


@router.get("/transactions", response_model=LoyaltyTransactionsResponse)
async def get_loyalty_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return loyalty ledger entries for the authenticated user."""
    rows = LoyaltyService.list_transactions(db, current_user.id)
    items = [
        LoyaltyTransactionItem(
            id=r.id,
            transaction_type=r.transaction_type,
            points=int(r.points),
            description=r.description,
            reference_id=r.reference_id,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return LoyaltyTransactionsResponse(transactions=items)


@router.post("/redeem", response_model=RedeemLoyaltyResponse)
async def redeem_points(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Redeem 50 loyalty points for one free duel entry credit.

    Credits are consumed during duel registration checkout when `use_free_entry` is true.
    """
    try:
        return LoyaltyService.redeem_for_free_duel_entry(db, current_user)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
