"""
Leaderboard API response schemas.

These models document the JSON returned by ``GET /api/v1/leaderboard/{duel_id}``
and ``GET /api/v1/leaderboard/my-rank/{duel_id}``.

Ranking uses ``UserAttempt.total_marks`` descending, then
``UserAttempt.time_taken_microseconds`` ascending (lower is better). Attempts
with NULL ``time_taken_microseconds`` are ordered after finite times for the
same marks. Only submitted attempts (``submitted_at`` set) appear on the board.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class LeaderboardReward(BaseModel):
    """
    Reward slot for a leaderboard row.

    Values are read from ``UserAttempt.reward_amount`` and
    ``UserAttempt.reward_status`` when present; settlement logic may fill these
    after the duel closes.
    """

    amount: Optional[float] = Field(
        default=None,
        description="Prize amount for this attempt when assigned; null until settled.",
    )
    status: str = Field(
        default="pending",
        description="Lifecycle: pending, processed, paid, etc.",
    )
    note: str = Field(
        default="Reward allocation is finalized after duel settlement.",
        description="Human-readable placeholder until rewards are wired end-to-end.",
    )


class LeaderboardEntry(BaseModel):
    """One row on the duel leaderboard."""

    rank: int = Field(
        ...,
        ge=1,
        description="1-based position after ordering by marks (desc) then time (asc, microseconds).",
    )
    display_name: str = Field(
        ...,
        description="User's profile name when set; otherwise a stable masked public label.",
    )
    marks: float = Field(
        ...,
        description="Total score from ``UserAttempt.total_marks``.",
    )
    time_microseconds: Optional[int] = Field(
        default=None,
        description="Total duration in microseconds from ``UserAttempt.time_taken_microseconds``.",
    )
    reward: LeaderboardReward = Field(
        ...,
        description="Reward metadata for this row (placeholder fields included for future payout UX).",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "rank": 1,
                    "display_name": "Ravi K.",
                    "marks": 12.5,
                    "time_microseconds": 420_000_000,
                    "reward": {
                        "amount": None,
                        "status": "pending",
                        "note": "Reward allocation is finalized after duel settlement.",
                    },
                }
            ]
        }
    }


class LeaderboardResponse(BaseModel):
    """Paginated leaderboard payload."""

    duel_id: str = Field(..., description="UUID of the daily duel.")
    total: int = Field(
        ...,
        ge=0,
        description="Number of submitted attempts included in ranking for this duel.",
    )
    limit: int = Field(..., ge=1, description="Maximum rows returned in this page.")
    offset: int = Field(..., ge=0, description="Number of leading rows skipped before this page.")
    entries: List[LeaderboardEntry] = Field(
        default_factory=list,
        description="Ordered slice of the leaderboard for the requested page.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "duel_id": "123e4567-e89b-12d3-a456-426614174000",
                    "total": 128,
                    "limit": 50,
                    "offset": 0,
                    "entries": [],
                }
            ]
        }
    }


class MyRankResponse(BaseModel):
    """Authenticated caller's leaderboard row for a duel."""

    duel_id: str = Field(..., description="UUID of the daily duel.")
    entry: LeaderboardEntry = Field(
        ...,
        description="The current user's ranked row, if they have a submitted attempt.",
    )
