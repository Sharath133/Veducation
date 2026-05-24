"""
Loyalty business logic: balances, ledger, redeem for free duel entry credits.
"""
from __future__ import annotations

from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.referral import LoyaltyTransaction
from app.models.user import User


class LoyaltyService:
    """Loyalty points and free-entry credits."""

    POINTS_PER_FREE_ENTRY = 50

    @staticmethod
    def build_balance_payload(user: User) -> Dict[str, Any]:
        """Return API-ready balance fields for the given user."""
        return {
            "loyalty_points": int(user.loyalty_points or 0),
            "free_duel_entry_credits": int(user.free_duel_entry_credits or 0),
            "points_per_free_entry": LoyaltyService.POINTS_PER_FREE_ENTRY,
        }

    @staticmethod
    def list_transactions(db: Session, user_id: UUID, limit: int = 50) -> List[LoyaltyTransaction]:
        """Return recent loyalty ledger rows for a user."""
        capped = max(1, min(limit, 100))
        return (
            db.query(LoyaltyTransaction)
            .filter(LoyaltyTransaction.user_id == user_id)
            .order_by(LoyaltyTransaction.created_at.desc())
            .limit(capped)
            .all()
        )

    @staticmethod
    def redeem_for_free_duel_entry(db: Session, user: User) -> Dict[str, Any]:
        """
        Spend POINTS_PER_FREE_ENTRY loyalty points for one free duel entry credit.

        Raises:
            ValueError: If the user does not have enough points.
        """
        balance = int(user.loyalty_points or 0)
        if balance < LoyaltyService.POINTS_PER_FREE_ENTRY:
            raise ValueError(
                "Insufficient loyalty points. "
                f"You have {balance} points; {LoyaltyService.POINTS_PER_FREE_ENTRY} "
                "points are required for one free duel entry."
            )

        user.loyalty_points = balance - LoyaltyService.POINTS_PER_FREE_ENTRY
        user.free_duel_entry_credits = int(user.free_duel_entry_credits or 0) + 1

        ledger = LoyaltyTransaction(
            user_id=user.id,
            transaction_type="redeemed",
            points=-LoyaltyService.POINTS_PER_FREE_ENTRY,
            reference_id=None,
            description="Redeemed points for one free duel entry",
        )
        db.add(ledger)
        db.commit()
        db.refresh(user)

        return {
            "loyalty_points": int(user.loyalty_points),
            "free_duel_entry_credits": int(user.free_duel_entry_credits),
            "points_redeemed": LoyaltyService.POINTS_PER_FREE_ENTRY,
            "message": "Redeemed 50 points for 1 free duel entry credit.",
        }
