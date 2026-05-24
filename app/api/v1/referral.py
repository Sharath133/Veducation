"""
Referral Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.referral import Referral
from app.models.user import User
from app.schemas.referral import ApplyReferralCodeRequest
from app.services.loyalty_service import LoyaltyService
from app.services.referral_service import ReferralService

router = APIRouter()


@router.get("/info")
async def get_referral_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get referral information"""
    total_referrals = (
        db.query(Referral).filter(Referral.referrer_id == current_user.id).count()
    )
    return {
        "referral_code": current_user.referral_code,
        "total_referrals": total_referrals,
        "loyalty_points_earned": current_user.loyalty_points,
        "points_per_referral": ReferralService.POINTS_PER_REFERRAL,
        "points_for_free_entry": LoyaltyService.POINTS_PER_FREE_ENTRY,
    }


@router.post("/apply-code")
async def apply_referral_code(
    body: ApplyReferralCodeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Apply referral code for the current user and credit the referrer."""
    try:
        return ReferralService.apply_referral_code(db, current_user, body.referral_code)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/earnings")
async def get_referral_earnings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get referral earnings"""
    total_referrals = (
        db.query(Referral).filter(Referral.referrer_id == current_user.id).count()
    )
    total_earnings = db.query(func.coalesce(func.sum(Referral.points_awarded), 0)).filter(
        Referral.referrer_id == current_user.id
    ).scalar()
    referrals = (
        db.query(Referral)
        .filter(Referral.referrer_id == current_user.id)
        .order_by(Referral.created_at.desc())
        .limit(50)
        .all()
    )
    referral_history = [
        {
            "referral_id": str(r.id),
            "referred_user_id": str(r.referred_id),
            "points_awarded": int(r.points_awarded or 0),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in referrals
    ]
    return {
        "total_referrals": total_referrals,
        "total_earnings": int(total_earnings or 0),
        "loyalty_points": current_user.loyalty_points,
        "referral_history": referral_history,
    }
