"""
Admin Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Form
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, cast, Date
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal
import csv
import io
import os
import uuid
from pathlib import Path

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.user import User
from app.models.duel import DailyDuel, Registration
from app.models.question import Question
from app.models.leaderboard import UserAnswer, UserAttempt
from app.models.pyq import PYQ, PYQQuestion, PYQCategory, PYQSection, PYQSectionPDF
from app.models.payment import Payment
from app.models.support_ticket import SupportTicket
from app.models.user_feedback import UserFeedback
from app.schemas.support import SupportTicketOut, SupportTicketStatusUpdate
from app.schemas.feedback import FeedbackOut
from app.schemas.admin_user_message import AdminMessageUserCreate
from app.models.admin_user_message import AdminUserMessage
from app.models.app_setting import AppSetting
from app.config import settings
from app.services.pyq_sections import (
    ensure_default_pyq_structure,
    next_pdf_order,
    pyq_upload_relative_path,
    serialize_pyq_structure,
)
from pydantic import BaseModel, Field
from app.api.v1.duel import (
    DEFAULT_DUEL_INSTRUCTIONS_EN,
    DEFAULT_DUEL_INSTRUCTIONS_TE,
    DUEL_INSTRUCTIONS_EN_KEY,
    DUEL_INSTRUCTIONS_TE_KEY,
)

router = APIRouter()


def _today_duel_date() -> str:
    """Return the app's duel calendar date using the configured IST timezone."""
    return datetime.now(ZoneInfo(settings.SETTLEMENT_TIMEZONE)).date().isoformat()


def _get_setting_value(db: Session, key: str, default: str) -> str:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row and row.value.strip():
        return row.value
    return default


def _upsert_setting(db: Session, key: str, value: str) -> None:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))


# ==================== SCHEMAS ====================

class DailyDuelCreate(BaseModel):
    """Create daily duel request"""
    duel_date: str = Field(..., description="Date in YYYY-MM-DD format")
    total_questions: int = Field(default=15, ge=1, le=50)
    time_limit_minutes: int = Field(default=15, ge=5, le=60)
    registration_fee: Decimal = Field(..., ge=0)
    prize_pool: Decimal = Field(default=0, ge=0)


class DailyDuelUpdate(BaseModel):
    """Update daily duel request"""
    total_questions: Optional[int] = Field(None, ge=1, le=50)
    time_limit_minutes: Optional[int] = Field(None, ge=5, le=60)
    registration_fee: Optional[Decimal] = Field(None, ge=0)
    prize_pool: Optional[Decimal] = Field(None, ge=0)
    status: Optional[str] = Field(None, pattern="^(upcoming|active|completed|settled)$")


class PYQCreate(BaseModel):
    """Create PYQ request"""
    title: str
    year: int
    month: Optional[str] = None
    subject: Optional[str] = None
    difficulty: str = Field(default="Medium", pattern="^(Easy|Medium|Hard)$")


class PYQSectionCreate(BaseModel):
    """Create a student-facing PYQ section."""
    category_id: Optional[str] = None
    category_code: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=160)
    display_order: int = 0


class PYQSectionUpdate(BaseModel):
    """Update a student-facing PYQ section."""
    category_id: Optional[str] = None
    category_code: Optional[str] = None
    title: Optional[str] = Field(None, min_length=1, max_length=160)
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class QuestionCreate(BaseModel):
    """Create question request"""
    question_text_en: str
    question_text_te: str
    option_a_en: str
    option_a_te: str
    option_b_en: str
    option_b_te: str
    option_c_en: str
    option_c_te: str
    option_d_en: str
    option_d_te: str
    correct_answer: str = Field(..., pattern="^[ABCD]$")
    marks: int = Field(default=1, ge=1)
    negative_marks: Decimal = Field(default=0.25, ge=0)
    question_order: int
    explanation_en: Optional[str] = None
    explanation_te: Optional[str] = None


class QuestionUpdate(BaseModel):
    """Update question request"""
    question_text_en: Optional[str] = None
    question_text_te: Optional[str] = None
    option_a_en: Optional[str] = None
    option_a_te: Optional[str] = None
    option_b_en: Optional[str] = None
    option_b_te: Optional[str] = None
    option_c_en: Optional[str] = None
    option_c_te: Optional[str] = None
    option_d_en: Optional[str] = None
    option_d_te: Optional[str] = None
    correct_answer: Optional[str] = Field(None, pattern="^[ABCD]$")
    marks: Optional[int] = Field(None, ge=1)
    negative_marks: Optional[Decimal] = Field(None, ge=0)
    question_order: Optional[int] = None
    explanation_en: Optional[str] = None
    explanation_te: Optional[str] = None


class DuelInstructionsUpdate(BaseModel):
    instructions_en: str = Field(..., min_length=1)
    instructions_te: str = Field(..., min_length=1)


# ==================== STATISTICS ====================

@router.get("/stats/overview")
async def get_overview_stats(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get overview statistics"""
    total_users = db.query(func.count(User.id)).scalar()
    total_registrations = db.query(func.count(Registration.id)).scalar()
    total_attempts = db.query(func.count(UserAttempt.id)).scalar()
    total_duels = db.query(func.count(DailyDuel.id)).scalar()
    
    # Today's stats
    today = _today_duel_date()
    today_duel = db.query(DailyDuel).filter(DailyDuel.duel_date == today).first()
    
    today_registrations = 0
    today_attempts = 0
    if today_duel:
        today_registrations = db.query(func.count(Registration.id)).filter(
            Registration.duel_id == today_duel.id,
            Registration.payment_status == "completed"
        ).scalar()
        today_attempts = db.query(func.count(UserAttempt.id)).filter(
            UserAttempt.duel_id == today_duel.id
        ).scalar()
    
    # Revenue stats
    total_revenue = db.query(func.sum(Payment.amount)).filter(
        Payment.status == "completed"
    ).scalar() or 0
    
    return {
        "total_users": total_users,
        "total_registrations": total_registrations,
        "total_attempts": total_attempts,
        "total_duels": total_duels,
        "today_registrations": today_registrations,
        "today_attempts": today_attempts,
        "total_revenue": float(total_revenue)
    }


@router.get("/stats/duel/{duel_id}")
async def get_duel_stats(
    duel_id: str,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get statistics for a specific duel"""
    try:
        duel_uuid = uuid.UUID(duel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid duel_id format")
    
    duel = db.query(DailyDuel).filter(DailyDuel.id == duel_uuid).first()
    if not duel:
        raise HTTPException(status_code=404, detail="Duel not found")
    
    registrations = db.query(func.count(Registration.id)).filter(
        Registration.duel_id == duel_uuid,
        Registration.payment_status == "completed"
    ).scalar()
    
    attempts = db.query(func.count(UserAttempt.id)).filter(
        UserAttempt.duel_id == duel_uuid
    ).scalar()
    
    submitted = db.query(func.count(UserAttempt.id)).filter(
        UserAttempt.duel_id == duel_uuid,
        UserAttempt.submitted_at.isnot(None)
    ).scalar()
    
    revenue = db.query(func.sum(Registration.payment_amount)).filter(
        Registration.duel_id == duel_uuid,
        Registration.payment_status == "completed"
    ).scalar() or 0
    
    return {
        "duel_id": str(duel.id),
        "duel_date": duel.duel_date,
        "status": duel.status,
        "total_registrations": registrations,
        "total_attempts": attempts,
        "submitted_attempts": submitted,
        "revenue": float(revenue),
        "prize_pool": float(duel.prize_pool)
    }


_MAX_RANKER_TIE = 9223372036854775807


@router.get("/stats/daily")
async def get_daily_stats(
    days: int = Query(14, ge=1, le=90),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Day-wise new users, completed duel registrations, registration revenue,
    and completed payment counts/amounts (by payment row timestamp).
    """
    tz = timezone.utc
    today = datetime.now(tz).date()
    start = today - timedelta(days=days - 1)
    start_dt = datetime(start.year, start.month, start.day, tzinfo=tz)

    reg_rows = (
        db.query(
            cast(Registration.registered_at, Date).label("d"),
            func.count(Registration.id),
            func.coalesce(func.sum(Registration.payment_amount), 0),
        )
        .filter(
            Registration.payment_status == "completed",
            Registration.registered_at >= start_dt,
        )
        .group_by(cast(Registration.registered_at, Date))
        .all()
    )
    reg_map = {r.d.isoformat(): {"registrations": int(r[1]), "registration_revenue": float(r[2])} for r in reg_rows}

    user_rows = (
        db.query(cast(User.created_at, Date).label("d"), func.count(User.id))
        .filter(User.created_at >= start_dt)
        .group_by(cast(User.created_at, Date))
        .all()
    )
    user_map = {r.d.isoformat(): int(r[1]) for r in user_rows}

    pay_ts = func.coalesce(Payment.updated_at, Payment.created_at)
    pay_rows = (
        db.query(
            cast(pay_ts, Date).label("d"),
            func.count(Payment.id),
            func.coalesce(func.sum(Payment.amount), 0),
        )
        .filter(Payment.status == "completed", Payment.created_at >= start_dt)
        .group_by(cast(pay_ts, Date))
        .all()
    )
    pay_map = {
        r.d.isoformat(): {"payments_count": int(r[1]), "payments_revenue": float(r[2])}
        for r in pay_rows
    }

    series = []
    d = start
    while d <= today:
        key = d.isoformat()
        r = reg_map.get(key, {"registrations": 0, "registration_revenue": 0.0})
        p = pay_map.get(key, {"payments_count": 0, "payments_revenue": 0.0})
        series.append(
            {
                "date": key,
                "new_users": user_map.get(key, 0),
                "completed_registrations": r["registrations"],
                "registration_revenue": r["registration_revenue"],
                "completed_payments_count": p["payments_count"],
                "payments_revenue": p["payments_revenue"],
            }
        )
        d += timedelta(days=1)

    return {"days": days, "series": series}


@router.get("/stats/top-rankers")
async def get_top_rankers_for_date(
    duel_date: str = Query(..., description="Duel calendar date YYYY-MM-DD"),
    limit: int = Query(10, ge=1, le=50),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Top submitted attempts for the duel scheduled on ``duel_date`` (marks, then time)."""
    duel = db.query(DailyDuel).filter(DailyDuel.duel_date == duel_date).first()
    if not duel:
        raise HTTPException(status_code=404, detail="No duel for this date")

    rows = (
        db.query(UserAttempt, User)
        .join(User, User.id == UserAttempt.user_id)
        .filter(
            UserAttempt.duel_id == duel.id,
            UserAttempt.submitted_at.isnot(None),
        )
        .order_by(
            func.coalesce(UserAttempt.total_marks, 0).desc(),
            func.coalesce(UserAttempt.time_taken_microseconds, _MAX_RANKER_TIE).asc(),
            UserAttempt.id.asc(),
        )
        .limit(limit)
        .all()
    )

    entries = []
    for i, (att, usr) in enumerate(rows, start=1):
        entries.append(
            {
                "rank": i,
                "user_id": str(usr.id),
                "display_name": (usr.name or "").strip() or usr.mobile_number,
                "mobile_number": usr.mobile_number,
                "total_marks": float(att.total_marks or 0),
                "time_taken_microseconds": att.time_taken_microseconds,
                "attempt_rank_column": att.rank,
                "submitted_at": att.submitted_at.isoformat() if att.submitted_at else None,
            }
        )

    return {
        "duel_date": duel_date,
        "duel_id": str(duel.id),
        "duel_status": duel.status,
        "limit": limit,
        "entries": entries,
    }


# ==================== DAILY DUEL MANAGEMENT ====================


@router.get("/duel-instructions")
async def get_duel_instructions_for_admin(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get editable duel instructions."""
    return {
        "instructions_en": _get_setting_value(
            db, DUEL_INSTRUCTIONS_EN_KEY, DEFAULT_DUEL_INSTRUCTIONS_EN
        ),
        "instructions_te": _get_setting_value(
            db, DUEL_INSTRUCTIONS_TE_KEY, DEFAULT_DUEL_INSTRUCTIONS_TE
        ),
    }


@router.put("/duel-instructions")
async def update_duel_instructions(
    payload: DuelInstructionsUpdate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Update duel instructions shown to students before a test."""
    _upsert_setting(db, DUEL_INSTRUCTIONS_EN_KEY, payload.instructions_en.strip())
    _upsert_setting(db, DUEL_INSTRUCTIONS_TE_KEY, payload.instructions_te.strip())
    db.commit()

    return {
        "message": "Duel instructions updated",
        "instructions_en": payload.instructions_en.strip(),
        "instructions_te": payload.instructions_te.strip(),
    }

@router.post("/duels")
async def create_daily_duel(
    duel_data: DailyDuelCreate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new daily duel"""
    # Check if duel for this date already exists
    existing = db.query(DailyDuel).filter(DailyDuel.duel_date == duel_data.duel_date).first()
    if existing:
        raise HTTPException(status_code=400, detail="Duel for this date already exists")
    
    duel = DailyDuel(
        id=uuid.uuid4(),
        duel_date=duel_data.duel_date,
        total_questions=duel_data.total_questions,
        time_limit_minutes=duel_data.time_limit_minutes,
        registration_fee=duel_data.registration_fee,
        prize_pool=duel_data.prize_pool,
        status="upcoming"
    )
    db.add(duel)
    db.commit()
    db.refresh(duel)
    
    return {
        "id": str(duel.id),
        "duel_date": duel.duel_date,
        "total_questions": duel.total_questions,
        "time_limit_minutes": duel.time_limit_minutes,
        "registration_fee": float(duel.registration_fee),
        "prize_pool": float(duel.prize_pool),
        "status": duel.status
    }


@router.get("/duels")
async def list_duels(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: Optional[str] = Query(None),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all duels"""
    query = db.query(DailyDuel)
    
    if status:
        query = query.filter(DailyDuel.status == status)
    
    total = query.count()
    duels = query.order_by(desc(DailyDuel.duel_date)).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "duels": [
            {
                "id": str(d.id),
                "duel_date": d.duel_date,
                "total_questions": d.total_questions,
                "time_limit_minutes": d.time_limit_minutes,
                "registration_fee": float(d.registration_fee),
                "prize_pool": float(d.prize_pool),
                "status": d.status,
                "created_at": d.created_at.isoformat() if d.created_at else None
            }
            for d in duels
        ]
    }


@router.get("/duels/{duel_id}")
async def get_duel(
    duel_id: str,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get a specific duel"""
    try:
        duel_uuid = uuid.UUID(duel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid duel_id format")
    
    duel = db.query(DailyDuel).filter(DailyDuel.id == duel_uuid).first()
    if not duel:
        raise HTTPException(status_code=404, detail="Duel not found")
    
    questions_count = db.query(func.count(Question.id)).filter(
        Question.duel_id == duel_uuid
    ).scalar()
    
    return {
        "id": str(duel.id),
        "duel_date": duel.duel_date,
        "total_questions": duel.total_questions,
        "time_limit_minutes": duel.time_limit_minutes,
        "registration_fee": float(duel.registration_fee),
        "prize_pool": float(duel.prize_pool),
        "status": duel.status,
        "questions_added": questions_count,
        "created_at": duel.created_at.isoformat() if duel.created_at else None
    }


@router.put("/duels/{duel_id}")
async def update_duel(
    duel_id: str,
    duel_data: DailyDuelUpdate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update a daily duel"""
    try:
        duel_uuid = uuid.UUID(duel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid duel_id format")
    
    duel = db.query(DailyDuel).filter(DailyDuel.id == duel_uuid).first()
    if not duel:
        raise HTTPException(status_code=404, detail="Duel not found")
    
    if duel_data.total_questions is not None:
        duel.total_questions = duel_data.total_questions
    if duel_data.time_limit_minutes is not None:
        duel.time_limit_minutes = duel_data.time_limit_minutes
    if duel_data.registration_fee is not None:
        duel.registration_fee = duel_data.registration_fee
    if duel_data.prize_pool is not None:
        duel.prize_pool = duel_data.prize_pool
    if duel_data.status is not None:
        duel.status = duel_data.status
    
    db.commit()
    db.refresh(duel)
    
    return {
        "id": str(duel.id),
        "duel_date": duel.duel_date,
        "total_questions": duel.total_questions,
        "time_limit_minutes": duel.time_limit_minutes,
        "registration_fee": float(duel.registration_fee),
        "prize_pool": float(duel.prize_pool),
        "status": duel.status
    }


@router.delete("/duels/{duel_id}")
async def delete_duel(
    duel_id: str,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete a daily duel (only if no registrations)"""
    try:
        duel_uuid = uuid.UUID(duel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid duel_id format")
    
    duel = db.query(DailyDuel).filter(DailyDuel.id == duel_uuid).first()
    if not duel:
        raise HTTPException(status_code=404, detail="Duel not found")
    
    # Check if there are registrations
    registrations_count = db.query(func.count(Registration.id)).filter(
        Registration.duel_id == duel_uuid
    ).scalar()
    
    if registrations_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete duel with existing registrations"
        )
    
    db.delete(duel)
    db.commit()
    
    return {"message": "Duel deleted successfully"}


# ==================== QUESTION MANAGEMENT FOR DUELS ====================

def _serialize_duel_question(question: Question) -> dict:
    return {
        "id": str(question.id),
        "duel_id": str(question.duel_id),
        "question_text_en": question.question_text_en,
        "question_text_te": question.question_text_te,
        "option_a_en": question.option_a_en,
        "option_a_te": question.option_a_te,
        "option_b_en": question.option_b_en,
        "option_b_te": question.option_b_te,
        "option_c_en": question.option_c_en,
        "option_c_te": question.option_c_te,
        "option_d_en": question.option_d_en,
        "option_d_te": question.option_d_te,
        "correct_answer": question.correct_answer,
        "marks": question.marks,
        "negative_marks": float(question.negative_marks),
        "question_order": question.question_order,
        "created_at": question.created_at.isoformat() if question.created_at else None,
    }


def _get_duel_or_404(db: Session, duel_id: str) -> tuple[uuid.UUID, DailyDuel]:
    try:
        duel_uuid = uuid.UUID(duel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid duel_id format")

    duel = db.query(DailyDuel).filter(DailyDuel.id == duel_uuid).first()
    if not duel:
        raise HTTPException(status_code=404, detail="Duel not found")
    return duel_uuid, duel


def _get_duel_question_or_404(
    db: Session,
    duel_uuid: uuid.UUID,
    question_id: str,
) -> Question:
    try:
        question_uuid = uuid.UUID(question_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid question_id format")

    question = db.query(Question).filter(
        Question.id == question_uuid,
        Question.duel_id == duel_uuid,
    ).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@router.get("/duels/{duel_id}/questions")
async def list_duel_questions(
    duel_id: str,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List all questions for a duel."""
    duel_uuid, duel = _get_duel_or_404(db, duel_id)
    questions = db.query(Question).filter(
        Question.duel_id == duel_uuid,
    ).order_by(Question.question_order, Question.created_at).all()

    return {
        "duel": {
            "id": str(duel.id),
            "duel_date": duel.duel_date,
            "status": duel.status,
            "total_questions": duel.total_questions,
        },
        "questions": [_serialize_duel_question(q) for q in questions],
    }


@router.post("/duels/{duel_id}/questions")
async def add_question_to_duel(
    duel_id: str,
    question_data: QuestionCreate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Add a question to a duel"""
    try:
        duel_uuid = uuid.UUID(duel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid duel_id format")
    
    duel = db.query(DailyDuel).filter(DailyDuel.id == duel_uuid).first()
    if not duel:
        raise HTTPException(status_code=404, detail="Duel not found")
    
    question = Question(
        id=uuid.uuid4(),
        duel_id=duel_uuid,
        question_text_en=question_data.question_text_en,
        question_text_te=question_data.question_text_te,
        option_a_en=question_data.option_a_en,
        option_a_te=question_data.option_a_te,
        option_b_en=question_data.option_b_en,
        option_b_te=question_data.option_b_te,
        option_c_en=question_data.option_c_en,
        option_c_te=question_data.option_c_te,
        option_d_en=question_data.option_d_en,
        option_d_te=question_data.option_d_te,
        correct_answer=question_data.correct_answer,
        marks=question_data.marks,
        negative_marks=question_data.negative_marks,
        question_order=question_data.question_order
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    
    return {
        "message": "Question added successfully",
        "question": _serialize_duel_question(question),
    }


@router.put("/duels/{duel_id}/questions/{question_id}")
async def update_duel_question(
    duel_id: str,
    question_id: str,
    question_data: QuestionUpdate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Edit a duel question, options, scoring, and correct answer."""
    duel_uuid, _duel = _get_duel_or_404(db, duel_id)
    question = _get_duel_question_or_404(db, duel_uuid, question_id)

    updates = question_data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if value is not None:
            setattr(question, field, value)

    db.commit()
    db.refresh(question)

    return {
        "message": "Question updated successfully",
        "question": _serialize_duel_question(question),
    }


@router.delete("/duels/{duel_id}/questions/{question_id}")
async def delete_duel_question(
    duel_id: str,
    question_id: str,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Delete a duel question if no submitted answers reference it."""
    duel_uuid, _duel = _get_duel_or_404(db, duel_id)
    question = _get_duel_question_or_404(db, duel_uuid, question_id)

    answers_count = db.query(func.count(UserAnswer.id)).filter(
        UserAnswer.question_id == question.id,
    ).scalar()
    if answers_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a question that already has user answers. Edit it instead.",
        )

    db.delete(question)
    db.commit()

    return {"message": "Question deleted successfully"}


def _upload_root() -> Path:
    root = Path(__file__).resolve().parents[3] / settings.UPLOAD_DIR
    root.mkdir(parents=True, exist_ok=True)
    return root


def _resolve_pyq_category(
    db: Session,
    category_id: Optional[str],
    category_code: Optional[str],
) -> PYQCategory:
    ensure_default_pyq_structure(db)

    if category_id:
        try:
            cid = uuid.UUID(category_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid category_id format")
        category = db.query(PYQCategory).filter(PYQCategory.id == cid).first()
    elif category_code:
        category = db.query(PYQCategory).filter(PYQCategory.code == category_code).first()
    else:
        raise HTTPException(status_code=400, detail="category_id or category_code is required")

    if not category:
        raise HTTPException(status_code=404, detail="PYQ category not found")
    return category


@router.post("/duels/{duel_id}/upload-csv")
async def upload_duel_questions_csv(
    duel_id: str,
    file: UploadFile = File(...),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Bulk-import duel questions from CSV (same columns as PYQ import except explanations).
    Headers: question_order,question_text_en,question_text_te,option_a_en,option_a_te,
    option_b_en,option_b_te,option_c_en,option_c_te,option_d_en,option_d_te,correct_answer,marks,negative_marks
    """
    try:
        duel_uuid = uuid.UUID(duel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid duel_id format")

    duel = db.query(DailyDuel).filter(DailyDuel.id == duel_uuid).first()
    if not duel:
        raise HTTPException(status_code=404, detail="Duel not found")

    contents = await file.read()
    csv_file = io.StringIO(contents.decode("utf-8"))
    reader = csv.DictReader(csv_file)

    questions_added = 0
    errors = []

    for row_num, row in enumerate(reader, start=2):
        try:
            q = Question(
                id=uuid.uuid4(),
                duel_id=duel_uuid,
                question_order=int(row.get("question_order", row_num - 1)),
                question_text_en=row["question_text_en"],
                question_text_te=row.get("question_text_te", row["question_text_en"]),
                option_a_en=row["option_a_en"],
                option_a_te=row.get("option_a_te", row["option_a_en"]),
                option_b_en=row["option_b_en"],
                option_b_te=row.get("option_b_te", row["option_b_en"]),
                option_c_en=row["option_c_en"],
                option_c_te=row.get("option_c_te", row["option_c_en"]),
                option_d_en=row["option_d_en"],
                option_d_te=row.get("option_d_te", row["option_d_en"]),
                correct_answer=row["correct_answer"].upper(),
                marks=int(row.get("marks", 1)),
                negative_marks=Decimal(row.get("negative_marks", 0.25)),
            )
            db.add(q)
            questions_added += 1
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")

    db.commit()

    return {
        "message": f"Successfully added {questions_added} questions",
        "questions_added": questions_added,
        "errors": errors if errors else None,
    }


# ==================== PYQ MANAGEMENT ====================

@router.post("/pyqs")
async def create_pyq(
    pyq_data: PYQCreate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new PYQ"""
    pyq = PYQ(
        id=uuid.uuid4(),
        title=pyq_data.title,
        year=pyq_data.year,
        month=pyq_data.month,
        subject=pyq_data.subject,
        difficulty=pyq_data.difficulty
    )
    db.add(pyq)
    db.commit()
    db.refresh(pyq)
    
    return {
        "id": str(pyq.id),
        "title": pyq.title,
        "year": pyq.year,
        "month": pyq.month,
        "subject": pyq.subject,
        "difficulty": pyq.difficulty
    }


@router.get("/pyqs")
async def list_pyqs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    year: Optional[int] = Query(None),
    subject: Optional[str] = Query(None),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all PYQs"""
    query = db.query(PYQ)
    
    if year:
        query = query.filter(PYQ.year == year)
    if subject:
        query = query.filter(PYQ.subject == subject)
    
    total = query.count()
    pyqs = query.order_by(desc(PYQ.year), desc(PYQ.created_at)).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "pyqs": [
            {
                "id": str(p.id),
                "title": p.title,
                "year": p.year,
                "month": p.month,
                "subject": p.subject,
                "difficulty": p.difficulty,
                "total_questions": p.total_questions,
                "is_active": p.is_active,
                "reference_pdf_path": p.reference_pdf_path,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in pyqs
        ]
    }


@router.post("/pyqs/{pyq_id}/questions")
async def add_question_to_pyq(
    pyq_id: str,
    question_data: QuestionCreate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Add a question to a PYQ"""
    try:
        pyq_uuid = uuid.UUID(pyq_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid pyq_id format")
    
    pyq = db.query(PYQ).filter(PYQ.id == pyq_uuid).first()
    if not pyq:
        raise HTTPException(status_code=404, detail="PYQ not found")
    
    question = PYQQuestion(
        id=uuid.uuid4(),
        pyq_id=pyq_uuid,
        question_text_en=question_data.question_text_en,
        question_text_te=question_data.question_text_te,
        option_a_en=question_data.option_a_en,
        option_a_te=question_data.option_a_te,
        option_b_en=question_data.option_b_en,
        option_b_te=question_data.option_b_te,
        option_c_en=question_data.option_c_en,
        option_c_te=question_data.option_c_te,
        option_d_en=question_data.option_d_en,
        option_d_te=question_data.option_d_te,
        correct_answer=question_data.correct_answer,
        marks=question_data.marks,
        negative_marks=question_data.negative_marks,
        question_order=question_data.question_order,
        explanation_en=question_data.explanation_en,
        explanation_te=question_data.explanation_te
    )
    db.add(question)
    
    # Update total_questions count
    pyq.total_questions = db.query(func.count(PYQQuestion.id)).filter(
        PYQQuestion.pyq_id == pyq_uuid
    ).scalar() + 1
    
    db.commit()
    db.refresh(question)
    
    return {
        "id": str(question.id),
        "question_order": question.question_order,
        "message": "Question added successfully"
    }


@router.post("/pyqs/{pyq_id}/upload-csv")
async def upload_pyq_csv(
    pyq_id: str,
    file: UploadFile = File(...),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Upload PYQ questions via CSV file"""
    try:
        pyq_uuid = uuid.UUID(pyq_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid pyq_id format")
    
    pyq = db.query(PYQ).filter(PYQ.id == pyq_uuid).first()
    if not pyq:
        raise HTTPException(status_code=404, detail="PYQ not found")
    
    # Read CSV file
    contents = await file.read()
    csv_file = io.StringIO(contents.decode('utf-8'))
    reader = csv.DictReader(csv_file)
    
    questions_added = 0
    errors = []
    
    # Expected CSV columns:
    # question_order, question_text_en, question_text_te, option_a_en, option_a_te,
    # option_b_en, option_b_te, option_c_en, option_c_te, option_d_en, option_d_te,
    # correct_answer, marks, negative_marks, explanation_en (optional), explanation_te (optional)
    
    for row_num, row in enumerate(reader, start=2):  # Start at 2 (row 1 is header)
        try:
            question = PYQQuestion(
                id=uuid.uuid4(),
                pyq_id=pyq_uuid,
                question_order=int(row.get('question_order', row_num - 1)),
                question_text_en=row['question_text_en'],
                question_text_te=row.get('question_text_te', row['question_text_en']),
                option_a_en=row['option_a_en'],
                option_a_te=row.get('option_a_te', row['option_a_en']),
                option_b_en=row['option_b_en'],
                option_b_te=row.get('option_b_te', row['option_b_en']),
                option_c_en=row['option_c_en'],
                option_c_te=row.get('option_c_te', row['option_c_en']),
                option_d_en=row['option_d_en'],
                option_d_te=row.get('option_d_te', row['option_d_en']),
                correct_answer=row['correct_answer'].upper(),
                marks=int(row.get('marks', 1)),
                negative_marks=Decimal(row.get('negative_marks', 0.25)),
                explanation_en=row.get('explanation_en'),
                explanation_te=row.get('explanation_te')
            )
            db.add(question)
            questions_added += 1
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
    
    # Update total_questions count
    pyq.total_questions = db.query(func.count(PYQQuestion.id)).filter(
        PYQQuestion.pyq_id == pyq_uuid
    ).scalar()
    
    db.commit()
    
    return {
        "message": f"Successfully added {questions_added} questions",
        "questions_added": questions_added,
        "errors": errors if errors else None
    }


@router.post("/pyqs/{pyq_id}/upload-pdf")
async def upload_pyq_reference_pdf(
    pyq_id: str,
    file: UploadFile = File(...),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Attach a reference PDF to a PYQ (stored under server upload dir)."""
    try:
        pyq_uuid = uuid.UUID(pyq_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid pyq_id format")

    pyq = db.query(PYQ).filter(PYQ.id == pyq_uuid).first()
    if not pyq:
        raise HTTPException(status_code=404, detail="PYQ not found")

    fname = (file.filename or "").lower()
    ct = (file.content_type or "").lower()
    if not fname.endswith(".pdf") and "pdf" not in ct:
        raise HTTPException(status_code=400, detail="File must be a PDF")

    raw = await file.read()
    if len(raw) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="PDF too large (max 25MB)")

    subdir = _upload_root() / "pyqs"
    subdir.mkdir(parents=True, exist_ok=True)
    dest_name = f"{pyq_uuid}.pdf"
    dest_path = subdir / dest_name
    dest_path.write_bytes(raw)

    rel = os.path.join(settings.UPLOAD_DIR, "pyqs", dest_name).replace("\\", "/")
    pyq.reference_pdf_path = rel
    db.commit()
    db.refresh(pyq)

    return {
        "message": "PDF uploaded",
        "reference_pdf_path": pyq.reference_pdf_path,
        "pyq_id": str(pyq.id),
    }


@router.get("/pyq-sections")
async def admin_list_pyq_sections(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List student-facing PYQ categories, sections, and PDFs for admin editing."""
    return {"categories": serialize_pyq_structure(db, include_inactive=True)}


@router.post("/pyq-sections")
async def admin_create_pyq_section(
    section_data: PYQSectionCreate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Create a new student-facing PYQ section under an existing category."""
    category = _resolve_pyq_category(
        db,
        section_data.category_id,
        section_data.category_code,
    )
    section = PYQSection(
        id=uuid.uuid4(),
        category_id=category.id,
        title=section_data.title.strip(),
        display_order=section_data.display_order,
    )
    db.add(section)
    db.commit()
    db.refresh(section)
    return {
        "id": str(section.id),
        "category_id": str(section.category_id),
        "title": section.title,
        "display_order": section.display_order,
        "is_active": section.is_active,
    }


@router.put("/pyq-sections/{section_id}")
async def admin_update_pyq_section(
    section_id: str,
    section_data: PYQSectionUpdate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Edit a student-facing PYQ section."""
    try:
        sid = uuid.UUID(section_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid section_id format")

    section = db.query(PYQSection).filter(PYQSection.id == sid).first()
    if not section:
        raise HTTPException(status_code=404, detail="PYQ section not found")

    if section_data.category_id is not None or section_data.category_code is not None:
        category = _resolve_pyq_category(
            db,
            section_data.category_id,
            section_data.category_code,
        )
        section.category_id = category.id
    if section_data.title is not None:
        section.title = section_data.title.strip()
    if section_data.display_order is not None:
        section.display_order = section_data.display_order
    if section_data.is_active is not None:
        section.is_active = section_data.is_active

    db.commit()
    db.refresh(section)
    return {
        "id": str(section.id),
        "category_id": str(section.category_id),
        "title": section.title,
        "display_order": section.display_order,
        "is_active": section.is_active,
    }


@router.post("/pyq-sections/{section_id}/pdfs")
async def admin_upload_pyq_section_pdf(
    section_id: str,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Upload a PDF under an existing student-facing PYQ section."""
    try:
        sid = uuid.UUID(section_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid section_id format")

    section = db.query(PYQSection).filter(PYQSection.id == sid).first()
    if not section:
        raise HTTPException(status_code=404, detail="PYQ section not found")

    fname = (file.filename or "").lower()
    ct = (file.content_type or "").lower()
    if not fname.endswith(".pdf") and "pdf" not in ct:
        raise HTTPException(status_code=400, detail="File must be a PDF")

    raw = await file.read()
    if len(raw) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="PDF too large (max 25MB)")

    pdf_id = uuid.uuid4()
    subdir = _upload_root() / "pyq-sections" / str(sid)
    subdir.mkdir(parents=True, exist_ok=True)
    dest_name = f"{pdf_id}.pdf"
    dest_path = subdir / dest_name
    dest_path.write_bytes(raw)

    rel = pyq_upload_relative_path(str(sid), dest_name)
    pdf = PYQSectionPDF(
        id=pdf_id,
        section_id=sid,
        title=(title or file.filename or "PYQ PDF").strip(),
        file_path=rel,
        display_order=next_pdf_order(db, sid),
    )
    db.add(pdf)
    db.commit()
    db.refresh(pdf)

    return {
        "id": str(pdf.id),
        "section_id": str(pdf.section_id),
        "title": pdf.title,
        "file_path": pdf.file_path,
        "url": f"/{pdf.file_path}",
        "display_order": pdf.display_order,
        "is_active": pdf.is_active,
    }


# ==================== USER MANAGEMENT ====================

@router.get("/users")
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    is_active: Optional[bool] = Query(None),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all users"""
    query = db.query(User)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    total = query.count()
    users = query.order_by(desc(User.created_at)).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "users": [
            {
                "id": str(u.id),
                "mobile_number": u.mobile_number,
                "name": u.name,
                "loyalty_points": u.loyalty_points,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None
            }
            for u in users
        ]
    }


@router.put("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: str,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Toggle user active status"""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    
    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = not user.is_active
    db.commit()
    
    return {
        "id": str(user.id),
        "is_active": user.is_active,
        "message": f"User {'activated' if user.is_active else 'deactivated'}"
    }


@router.post("/users/{user_id}/message")
async def admin_send_message_to_user(
    user_id: str,
    payload: AdminMessageUserCreate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Store an in-app message for the user (retrieved via authenticated user API)."""
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    target = db.query(User).filter(User.id == user_uuid).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    row = AdminUserMessage(
        id=uuid.uuid4(),
        user_id=user_uuid,
        title=payload.title,
        body=payload.body,
        created_by_admin_id=current_admin.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "id": str(row.id),
        "user_id": str(user_uuid),
        "message": "Message saved; user can read it in the app inbox.",
    }


# ==================== SUPPORT TICKETS ====================


@router.get("/support/tickets")
async def admin_list_support_tickets(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(
        None,
        pattern="^(open|in_progress|resolved|closed)$",
    ),
    user_id: Optional[str] = Query(None, description="Filter by submitting user id"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List all support tickets (paginated)."""
    q = db.query(SupportTicket)
    if status:
        q = q.filter(SupportTicket.status == status)
    if user_id:
        try:
            uid = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user_id format")
        q = q.filter(SupportTicket.user_id == uid)

    total = q.count()
    rows = (
        q.join(User, User.id == SupportTicket.user_id)
        .add_columns(User.mobile_number)
        .order_by(desc(SupportTicket.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    tickets_out = []
    for row in rows:
        t = row[0]
        mobile = row[1]
        d = SupportTicketOut.model_validate(t).model_dump()
        d["user_mobile"] = mobile
        tickets_out.append(d)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "tickets": tickets_out,
    }


@router.patch("/support/tickets/{ticket_id}")
async def admin_update_support_ticket_status(
    ticket_id: str,
    body: SupportTicketStatusUpdate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Update support ticket status."""
    try:
        tid = uuid.UUID(ticket_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ticket_id format")

    ticket = db.query(SupportTicket).filter(SupportTicket.id == tid).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Support ticket not found")

    ticket.status = body.status
    db.commit()
    db.refresh(ticket)
    return SupportTicketOut.model_validate(ticket).model_dump()


# ==================== USER FEEDBACK ====================


@router.get("/feedback")
async def admin_list_feedback(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    category: Optional[str] = Query(
        None,
        pattern="^(suggestion|bug|feature_request|other)$",
    ),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List user feedback and suggestions (paginated)."""
    q = db.query(UserFeedback)
    if category:
        q = q.filter(UserFeedback.category == category)

    total = q.count()
    rows = (
        q.join(User, User.id == UserFeedback.user_id)
        .add_columns(User.mobile_number)
        .order_by(desc(UserFeedback.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    items_out = []
    for row in rows:
        f = row[0]
        mobile = row[1]
        d = FeedbackOut.model_validate(f).model_dump()
        d["user_mobile"] = mobile
        items_out.append(d)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items_out,
    }
