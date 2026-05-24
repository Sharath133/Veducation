"""
Unit tests for duel attempt scoring and submit response shaping.
"""
from decimal import Decimal
from uuid import uuid4

import pytest

from app.services.duel_scoring import (
    AttemptScoreSnapshot,
    QuestionScoreInput,
    compute_duel_attempt_score,
    format_submit_test_api_payload,
)


def _q(marks: int = 1, neg: str = "0.25"):
    qid = uuid4()
    return QuestionScoreInput(
        question_id=qid,
        correct_answer="A",
        marks=marks,
        negative_marks=Decimal(neg),
    )


def test_all_blank_no_selections():
    q1, q2, q3 = _q(), _q(), _q()
    snap = compute_duel_attempt_score([q1, q2, q3], {})
    assert snap.total_marks == Decimal("0")
    assert snap.correct_answers == 0
    assert snap.wrong_answers == 0
    assert snap.unanswered == 3


def test_all_blank_explicit_none_in_map():
    q1, q2 = _q(), _q()
    snap = compute_duel_attempt_score(
        [q1, q2],
        {q1.question_id: None, q2.question_id: "  "},
    )
    assert snap.unanswered == 2
    assert snap.total_marks == Decimal("0")


def test_partial_attempt_only_some_answered():
    q1, q2, q3 = _q(), _q(), _q()
    snap = compute_duel_attempt_score(
        [q1, q2, q3],
        {q1.question_id: "A", q2.question_id: "B"},
    )
    assert snap.correct_answers == 1
    assert snap.wrong_answers == 1
    assert snap.unanswered == 1
    assert snap.total_marks == Decimal("0.75")


def test_per_question_marks_and_negative_marks():
    q1 = QuestionScoreInput(
        question_id=uuid4(),
        correct_answer="C",
        marks=4,
        negative_marks=Decimal("1"),
    )
    q2 = QuestionScoreInput(
        question_id=uuid4(),
        correct_answer="D",
        marks=2,
        negative_marks=Decimal("0.5"),
    )
    snap = compute_duel_attempt_score(
        [q1, q2],
        {q1.question_id: "C", q2.question_id: "A"},
    )
    assert snap.correct_answers == 1
    assert snap.wrong_answers == 1
    assert snap.total_marks == Decimal("3.5")


def test_compute_score_deterministic_idempotent():
    qs = [_q(), _q(), _q()]
    sel = {qs[0].question_id: "A", qs[1].question_id: "B", qs[2].question_id: None}
    a = compute_duel_attempt_score(qs, sel)
    b = compute_duel_attempt_score(qs, sel)
    assert a == b
    assert isinstance(a, AttemptScoreSnapshot)


def test_format_submit_payload_stable_for_replay():
    aid = uuid4()
    p1 = format_submit_test_api_payload(
        aid,
        Decimal("3.5"),
        1_500_000,
        correct_answers=2,
        wrong_answers=1,
        unanswered=0,
    )
    p2 = format_submit_test_api_payload(
        aid,
        Decimal("3.5"),
        1_500_000,
        correct_answers=2,
        wrong_answers=1,
        unanswered=0,
    )
    assert p1 == p2
    assert p1["total_marks"] == 3.5
    assert p1["time_taken_seconds"] == 1.5
    assert p1["correct_answers"] == 2
    assert p1["wrong_answers"] == 1
    assert p1["unanswered"] == 0


def test_outcomes_match_per_question_marks():
    q1 = _q(marks=2, neg="0.5")
    snap = compute_duel_attempt_score([q1], {q1.question_id: "A"})
    assert len(snap.outcomes) == 1
    assert snap.outcomes[0].is_correct is True
    assert snap.outcomes[0].marks_obtained == Decimal("2")

    snap_w = compute_duel_attempt_score([q1], {q1.question_id: "B"})
    assert snap_w.outcomes[0].is_correct is False
    assert snap_w.outcomes[0].marks_obtained == Decimal("-0.5")


@pytest.mark.parametrize("raw", ("a", " A\t"))
def test_selection_normalization_correct(raw):
    q1 = _q()
    snap = compute_duel_attempt_score([q1], {q1.question_id: raw})
    assert snap.correct_answers == 1
