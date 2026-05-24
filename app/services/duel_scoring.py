"""
Pure scoring helpers for duel attempts (unit-testable, no HTTP/DB).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Mapping, Optional
from uuid import UUID


@dataclass(frozen=True)
class QuestionScoreInput:
    """Per-question data required to score an attempt."""

    question_id: UUID
    correct_answer: str
    marks: int
    negative_marks: Decimal


@dataclass(frozen=True)
class QuestionOutcome:
    """Scoring result for a single question."""

    question_id: UUID
    is_correct: Optional[bool]
    marks_obtained: Decimal


@dataclass(frozen=True)
class AttemptScoreSnapshot:
    """Aggregated scoring for a full attempt."""

    total_marks: Decimal
    correct_answers: int
    wrong_answers: int
    unanswered: int
    outcomes: tuple[QuestionOutcome, ...]


def _normalize_selection(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    return s.upper()


def compute_duel_attempt_score(
    questions: Iterable[QuestionScoreInput],
    selections: Mapping[UUID, Optional[str]],
) -> AttemptScoreSnapshot:
    """
    Score an attempt using per-question marks and negative_marks from the duel.

    - Correct: +marks (from question)
    - Wrong: -negative_marks (from question)
    - Blank / not attempted: 0 (no row or selection normalized to None)

    ``selections`` maps question_id -> selected option (A-D) or None/blank.
    Missing keys are treated as unanswered.
    """
    total = Decimal("0")
    correct = 0
    wrong = 0
    unanswered = 0
    outcomes: list[QuestionOutcome] = []

    for q in questions:
        sel = _normalize_selection(selections.get(q.question_id))
        if sel is None:
            unanswered += 1
            outcomes.append(
                QuestionOutcome(
                    question_id=q.question_id,
                    is_correct=None,
                    marks_obtained=Decimal("0"),
                )
            )
            continue
        if sel == q.correct_answer:
            correct += 1
            gained = Decimal(q.marks)
            total += gained
            outcomes.append(
                QuestionOutcome(
                    question_id=q.question_id,
                    is_correct=True,
                    marks_obtained=gained,
                )
            )
        else:
            wrong += 1
            lost = Decimal(q.negative_marks)
            total -= lost
            outcomes.append(
                QuestionOutcome(
                    question_id=q.question_id,
                    is_correct=False,
                    marks_obtained=-lost,
                )
            )

    return AttemptScoreSnapshot(
        total_marks=total,
        correct_answers=correct,
        wrong_answers=wrong,
        unanswered=unanswered,
        outcomes=tuple(outcomes),
    )


def format_submit_test_api_payload(
    attempt_id: UUID,
    total_marks: Decimal,
    time_taken_microseconds: Optional[int],
    *,
    correct_answers: int = 0,
    wrong_answers: int = 0,
    unanswered: int = 0,
) -> dict:
    """Stable JSON body for POST /submit (including idempotent replays)."""
    us = time_taken_microseconds or 0
    return {
        "attempt_id": str(attempt_id),
        "message": "Test submitted successfully",
        "total_marks": float(total_marks),
        "time_taken_seconds": us / 1_000_000,
        "correct_answers": correct_answers,
        "wrong_answers": wrong_answers,
        "unanswered": unanswered,
    }
