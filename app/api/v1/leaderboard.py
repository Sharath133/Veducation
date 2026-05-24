"""
Leaderboard Endpoints
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.duel import DailyDuel
from app.models.leaderboard import UserAttempt
from app.models.user import User
from app.schemas.leaderboard import (
    LeaderboardEntry,
    LeaderboardResponse,
    LeaderboardReward,
    MyRankResponse,
)

router = APIRouter()

# Treat missing duration as slowest tie-break among equal marks (asc microseconds).
_MAX_BIGINT = 9223372036854775807


def _public_display_name(*, name: Optional[str], user_id: uuid.UUID) -> str:
    cleaned = (name or "").strip()
    if cleaned:
        return cleaned
    uid = str(user_id).replace("-", "")
    return f"Player_{uid[:8]}"


def _reward_from_attempt(
    reward_amount: Optional[Decimal], reward_status: Optional[str]
) -> LeaderboardReward:
    amount = float(reward_amount) if reward_amount is not None else None
    st = reward_status or "pending"
    return LeaderboardReward(amount=amount, status=st)


def _leaderboard_order_columns():
    return (
        func.coalesce(UserAttempt.total_marks, 0).desc(),
        func.coalesce(UserAttempt.time_taken_microseconds, _MAX_BIGINT).asc(),
        UserAttempt.id.asc(),
    )


def _ranked_attempts_subquery(duel_uuid: uuid.UUID):
    lb_rank = (
        func.row_number()
        .over(order_by=_leaderboard_order_columns())
        .label("leaderboard_rank")
    )
    return (
        select(
            UserAttempt.id.label("attempt_id"),
            UserAttempt.user_id.label("user_id"),
            UserAttempt.total_marks.label("total_marks"),
            UserAttempt.time_taken_microseconds.label("time_taken_microseconds"),
            UserAttempt.reward_amount.label("reward_amount"),
            UserAttempt.reward_status.label("reward_status"),
            User.name.label("user_name"),
            lb_rank,
        )
        .select_from(UserAttempt)
        .join(User, User.id == UserAttempt.user_id)
        .where(
            UserAttempt.duel_id == duel_uuid,
            UserAttempt.submitted_at.is_not(None),
        )
    ).subquery()


def _row_to_entry(
    rank: int,
    display_name: str,
    marks: Optional[Decimal],
    time_us: Optional[int],
    reward_amount: Optional[Decimal],
    reward_status: Optional[str],
) -> LeaderboardEntry:
    return LeaderboardEntry(
        rank=rank,
        display_name=display_name,
        marks=float(marks or 0),
        time_microseconds=time_us,
        reward=_reward_from_attempt(reward_amount, reward_status),
    )


@router.get(
    "/{duel_id}",
    response_model=LeaderboardResponse,
    summary="Public duel leaderboard",
    response_description="Ordered submitted attempts with rank, display label, marks, time, and reward stub.",
)
async def get_leaderboard(
    duel_id: str,
    db: Session = Depends(get_db),
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="Page size (max 200).",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Rows to skip before returning the page.",
    ),
):
    """
    Return a paginated leaderboard for ``duel_id``.

    Rows are **submitted** attempts only, ordered by ``total_marks`` descending
    then ``time_taken_microseconds`` ascending (faster is better when marks tie).
    """
    try:
        duel_uuid = uuid.UUID(duel_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="duel_id must be a UUID",
        ) from exc

    duel_exists = db.scalar(select(func.count()).select_from(DailyDuel).where(DailyDuel.id == duel_uuid))
    if not duel_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Duel not found")

    ranked = _ranked_attempts_subquery(duel_uuid)
    total = db.scalar(select(func.count()).select_from(ranked)) or 0

    page_stmt = select(ranked).order_by(ranked.c.leaderboard_rank).offset(offset).limit(limit)
    rows = db.execute(page_stmt).all()

    entries: list[LeaderboardEntry] = []
    for row in rows:
        display_name = _public_display_name(name=row.user_name, user_id=row.user_id)
        entries.append(
            _row_to_entry(
                rank=int(row.leaderboard_rank),
                display_name=display_name,
                marks=row.total_marks,
                time_us=row.time_taken_microseconds,
                reward_amount=row.reward_amount,
                reward_status=row.reward_status,
            )
        )

    return LeaderboardResponse(
        duel_id=str(duel_uuid),
        total=int(total),
        limit=limit,
        offset=offset,
        entries=entries,
    )


@router.get(
    "/my-rank/{duel_id}",
    response_model=MyRankResponse,
    summary="Current user's duel rank",
    response_description="The authenticated user's leaderboard row for the duel.",
)
async def get_my_rank(
    duel_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Requires a Bearer token. Returns 404 if the user has no submitted attempt for the duel."""
    try:
        duel_uuid = uuid.UUID(duel_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="duel_id must be a UUID",
        ) from exc

    duel_exists = db.scalar(select(func.count()).select_from(DailyDuel).where(DailyDuel.id == duel_uuid))
    if not duel_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Duel not found")

    ranked = _ranked_attempts_subquery(duel_uuid)
    stmt = select(ranked).where(ranked.c.user_id == current_user.id)
    row = db.execute(stmt).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No submitted attempt for this duel",
        )

    display_name = _public_display_name(
        name=current_user.name, user_id=current_user.id
    )
    entry = _row_to_entry(
        rank=int(row.leaderboard_rank),
        display_name=display_name,
        marks=row.total_marks,
        time_us=row.time_taken_microseconds,
        reward_amount=row.reward_amount,
        reward_status=row.reward_status,
    )
    return MyRankResponse(duel_id=str(duel_uuid), entry=entry)
