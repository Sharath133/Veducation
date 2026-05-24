"""
Rewards Endpoints
"""
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.duel import DailyDuel
from app.models.payment import Reward
from app.models.user import User
from app.schemas.rewards import RewardHistoryItem, RewardHistoryResponse

router = APIRouter()


@router.get("/history", response_model=RewardHistoryResponse)
async def get_rewards_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List current user's settlement rewards (joined with duel date)."""
    rows = (
        db.query(Reward, DailyDuel.duel_date)
        .join(DailyDuel, Reward.duel_id == DailyDuel.id)
        .filter(Reward.user_id == current_user.id)
        .order_by(Reward.created_at.desc())
        .all()
    )

    items: list[RewardHistoryItem] = []
    for reward, duel_date in rows:
        amount: Decimal = reward.reward_amount
        items.append(
            RewardHistoryItem(
                id=reward.id,
                duel_date=duel_date,
                rank=reward.rank,
                reward_amount=f"{amount:.2f}",
                payment_status=reward.payment_status or "pending",
                created_at=reward.created_at,
                processed_at=reward.processed_at,
            )
        )

    return RewardHistoryResponse(items=items)


@router.get("/stats")
async def get_rewards_stats():
    """Get rewards statistics"""
    return {"message": "Rewards stats endpoint"}

