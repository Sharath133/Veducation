"""
Referral application: persist relationship and grant referrer loyalty points.
"""
from __future__ import annotations

from typing import Any, Dict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.referral import LoyaltyTransaction, Referral
from app.models.user import User
from app.utils.validators import validate_referral_code


class ReferralService:
    """Referral code application and rewards."""

    POINTS_PER_REFERRAL = 10

    @staticmethod
    def _normalize_code(referral_code: str) -> str:
        return (referral_code or "").strip().upper()

    @staticmethod
    def apply_referral_code(db: Session, referred_user: User, referral_code: str) -> Dict[str, Any]:
        """
        Link referred_user to referrer, create Referral row, credit referrer points + ledger.

        Raises:
            ValueError: Invalid code, self-referral, duplicate apply, or format errors.
        """
        code = ReferralService._normalize_code(referral_code)
        if not code:
            raise ValueError("Referral code is required.")
        if not validate_referral_code(code):
            raise ValueError("Referral code format is invalid.")

        if referred_user.referred_by_id is not None:
            raise ValueError("A referral has already been applied to this account.")

        existing = (
            db.query(Referral).filter(Referral.referred_id == referred_user.id).first()
        )
        if existing:
            raise ValueError("A referral has already been recorded for this account.")

        referrer = (
            db.query(User)
            .filter(func.upper(User.referral_code) == code)
            .first()
        )
        if not referrer:
            raise ValueError("Invalid referral code.")
        if referrer.id == referred_user.id:
            raise ValueError("You cannot use your own referral code.")

        referral_row = Referral(
            referrer_id=referrer.id,
            referred_id=referred_user.id,
            points_awarded=ReferralService.POINTS_PER_REFERRAL,
        )
        db.add(referral_row)
        db.flush()

        referred_user.referred_by_id = referrer.id

        referrer.loyalty_points = int(referrer.loyalty_points or 0) + ReferralService.POINTS_PER_REFERRAL
        db.add(
            LoyaltyTransaction(
                user_id=referrer.id,
                transaction_type="earned",
                points=ReferralService.POINTS_PER_REFERRAL,
                reference_id=referral_row.id,
                description="Referral reward",
            )
        )

        db.commit()
        db.refresh(referred_user)
        db.refresh(referrer)

        return {
            "success": True,
            "message": "Referral code applied successfully.",
            "loyalty_points_added": ReferralService.POINTS_PER_REFERRAL,
            "referrer_id": str(referrer.id),
        }
