"""
Duel Endpoints
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from app.database import get_db
from app.config import settings
from app.dependencies import get_current_user
from app.models.app_setting import AppSetting
from app.models.duel import DailyDuel, Registration
from app.models.question import Question
from app.models.leaderboard import UserAttempt, UserAnswer
from app.schemas.duel import (
    StartTestRequest,
    SubmitAnswerRequest,
    SubmitTestRequest,
    TimerStartRequest,
)
from app.services.duel_scoring import (
    QuestionScoreInput,
    compute_duel_attempt_score,
    format_submit_test_api_payload,
)
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

DUEL_INSTRUCTIONS_EN_KEY = "duel_instructions_en"
DUEL_INSTRUCTIONS_TE_KEY = "duel_instructions_te"

DEFAULT_DUEL_INSTRUCTIONS_EN = """INSTRUCTIONS TO TEST
1. The test will comprise of 15 to 20 Objective type Multiple Choice Questions (MCQs).
2. The candidates must select the language in which he/she wants to write the test.
3. The Time of the test begins only when the 'Start Test' button is pressed.
4. The candidates just need to click on the Right Choice / Correct option from the multiple choices / options given with each question. For Multiple Choice Questions, each question has four options, and the candidate has to click the appropriate option.
5. The Candidate can move to Previous and next questions by clicking on the buttons with respective labels displayed on screen throughout the test.
6. The candidate can Review the answered as well as the unanswered questions.
7. The answers can be changed at any time during the test and are saved automatically.
8. The candidates shall submit the test after attempting it, else the system automatically submits the test after allotted time.
9. The Time remaining is shown in the Right Top Corner of the screen.
10. All questions carry 1 mark each and there exists a negative marking of 0.25 for every wrong answer.
11. The candidates shall note that the top 10 rankers of the test will be rewarded cash prize or gift cards, according to their rank.
12. In tabulating ranks of the candidates, the system takes total marks secured after deducting marks for wrong answers and if two or more candidates got equal marks then the candidate with lowest time taken will be ranked higher in leaderboard where even micro-seconds will be counted."""

DEFAULT_DUEL_INSTRUCTIONS_TE = """పరీక్షకు సూచనలు
1. ఈ పరీక్షలో 15 నుండి 20 ఆబ్జెక్టివ్ తరహా బహుళైచ్ఛిక ప్రశ్నలు (MCQలు) ఉంటాయి.
2. అభ్యర్థులు తాము ఏ భాషలో పరీక్ష రాయాలనుకుంటున్నారో ఆ భాషను ఎంచుకోవాలి.
3. 'పరీక్ష ప్రారంభించు' బటన్‌ను నొక్కినప్పుడు మాత్రమే పరీక్ష సమయం ప్రారంభమవుతుంది.
4. అభ్యర్థులు ప్రతి ప్రశ్నకు ఇచ్చిన బహుళ ఎంపికల నుండి సరైన ఎంపికపై క్లిక్ చేయాలి. బహుళైచ్ఛిక ప్రశ్నలకు, ప్రతి ప్రశ్నకు నాలుగు ఎంపికలు ఉంటాయి మరియు అభ్యర్థి సరైన ఎంపికను క్లిక్ చేయాలి.
5. పరీక్ష అంతటా స్క్రీన్‌పై ప్రదర్శించబడే సంబంధిత లేబుల్స్ ఉన్న బటన్‌లను క్లిక్ చేయడం ద్వారా అభ్యర్థి మునుపటి మరియు తదుపరి ప్రశ్నలకు వెళ్ళవచ్చు.
6. అభ్యర్థి సమాధానమిచ్చిన మరియు సమాధానం ఇవ్వని ప్రశ్నలను సమీక్షించవచ్చు.
7. పరీక్ష సమయంలో ఎప్పుడైనా సమాధానాలను మార్చవచ్చు మరియు అవి స్వయంచాలకంగా సేవ్ చేయబడతాయి.
8. అభ్యర్థులు పరీక్ష రాసిన తర్వాత దానిని సబ్మిట్ చేయాలి, లేకపోతే కేటాయించిన సమయం తర్వాత సిస్టమ్ స్వయంచాలకంగా పరీక్షను సబ్మిట్ చేస్తుంది.
9. మిగిలిన సమయం స్క్రీన్ కుడి పైభాగంలో చూపబడుతుంది.
10. అన్ని ప్రశ్నలకు ఒక్కో దానికి 1 మార్కు ఉంటుంది మరియు ప్రతి తప్పు సమాధానానికి 0.25 నెగటివ్ మార్కింగ్ ఉంటుంది.
11. పరీక్షలో మొదటి 10 ర్యాంకులు సాధించిన వారికి వారి ర్యాంకు ప్రకారం నగదు బహుమతి లేదా గిఫ్ట్ కార్డులు బహుమతిగా ఇవ్వబడతాయని అభ్యర్థులు గమనించాలి.
12. అభ్యర్థుల ర్యాంకులను లెక్కించేటప్పుడు, తప్పు సమాధానాలకు మార్కులు తీసివేసిన తర్వాత పొందిన మొత్తం మార్కులను సిస్టమ్ పరిగణనలోకి తీసుకుంటుంది మరియు ఇద్దరు లేదా అంతకంటే ఎక్కువ మంది అభ్యర్థులకు సమాన మార్కులు వస్తే, తక్కువ సమయం తీసుకున్న అభ్యర్థికి లీడర్‌బోర్డ్‌లో ఉన్నత ర్యాంకు ఇవ్వబడుతుంది, ఇక్కడ మైక్రో-సెకన్లు కూడా పరిగణించబడతాయి."""


def _setting_value(db: Session, key: str, default: str) -> str:
    setting = db.query(AppSetting).filter(AppSetting.key == key).first()
    if setting and setting.value.strip():
        return setting.value
    return default


def _today_duel_date() -> str:
    """Return the app's duel calendar date using the configured IST timezone."""
    return datetime.now(ZoneInfo(settings.SETTLEMENT_TIMEZONE)).date().isoformat()


def _parse_uuid(value: str, field_label: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value).strip())
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_label} format: {e}",
        ) from e


def _attempt_total_marks_decimal(attempt: UserAttempt) -> Decimal:
    raw = attempt.total_marks
    if raw is None:
        return Decimal("0")
    if isinstance(raw, Decimal):
        return raw
    return Decimal(str(raw))


@router.get("/today")
async def get_today_duel(db: Session = Depends(get_db)):
    """Get today's duel"""
    today = _today_duel_date()
    
    duel = db.query(DailyDuel).filter(DailyDuel.duel_date == today).first()
    
    if not duel:
        raise HTTPException(status_code=404, detail="No duel available for today")
    
    return {
        "id": str(duel.id),
        "duel_date": duel.duel_date,
        "total_questions": duel.total_questions,
        "time_limit_minutes": duel.time_limit_minutes,
        "registration_fee": float(duel.registration_fee),
        "prize_pool": float(duel.prize_pool),
        "status": duel.status
    }


@router.post("/register")
async def register_duel(
    request: dict,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Register for today's duel"""
    # Registration will be handled after payment verification
    return {"message": "Registration will be completed after payment"}


@router.get("/registration-status")
async def get_registration_status(
    duel_id: str = Query(..., description="Duel ID"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the current user's registration and attempt status for a duel."""
    duel_uuid = _parse_uuid(duel_id, "duel_id")

    duel = db.query(DailyDuel).filter(DailyDuel.id == duel_uuid).first()
    if not duel:
        raise HTTPException(status_code=404, detail="Duel not found")

    registration = (
        db.query(Registration)
        .filter(
            Registration.duel_id == duel_uuid,
            Registration.user_id == current_user.id,
        )
        .first()
    )

    if not registration:
        return {
            "registered": False,
            "registration_id": None,
            "payment_status": None,
            "can_start": False,
            "attempt_id": None,
            "attempt_submitted": False,
            "result": None,
        }

    attempt = (
        db.query(UserAttempt)
        .filter(UserAttempt.registration_id == registration.id)
        .first()
    )
    is_paid = registration.payment_status == "completed"
    result = None
    if attempt and attempt.submitted_at:
        result = format_submit_test_api_payload(
            attempt.id,
            _attempt_total_marks_decimal(attempt),
            attempt.time_taken_microseconds,
            correct_answers=attempt.correct_answers or 0,
            wrong_answers=attempt.wrong_answers or 0,
            unanswered=attempt.unanswered or 0,
        )

    return {
        "registered": is_paid,
        "registration_id": str(registration.id),
        "payment_status": registration.payment_status,
        "can_start": is_paid and result is None,
        "attempt_id": str(attempt.id) if attempt else None,
        "attempt_submitted": result is not None,
        "result": result,
    }


@router.get("/instructions")
async def get_instructions(db: Session = Depends(get_db)):
    """Get test instructions"""
    return {
        "instructions_en": _setting_value(
            db, DUEL_INSTRUCTIONS_EN_KEY, DEFAULT_DUEL_INSTRUCTIONS_EN
        ),
        "instructions_te": _setting_value(
            db, DUEL_INSTRUCTIONS_TE_KEY, DEFAULT_DUEL_INSTRUCTIONS_TE
        ),
    }


@router.get("/questions")
async def get_questions(duel_id: str = Query(..., description="Duel ID"), db: Session = Depends(get_db)):
    """Get questions for test"""
    questions = db.query(Question).filter(
        Question.duel_id == duel_id
    ).order_by(Question.question_order).all()
    
    if not questions:
        raise HTTPException(status_code=404, detail="No questions found for this duel")
    
    return [
        {
            "id": str(q.id),
            "question_text_en": q.question_text_en,
            "question_text_te": q.question_text_te,
            "option_a_en": q.option_a_en,
            "option_a_te": q.option_a_te,
            "option_b_en": q.option_b_en,
            "option_b_te": q.option_b_te,
            "option_c_en": q.option_c_en,
            "option_c_te": q.option_c_te,
            "option_d_en": q.option_d_en,
            "option_d_te": q.option_d_te,
            "correct_answer": q.correct_answer,
            "marks": q.marks,
            "negative_marks": float(q.negative_marks),
            "question_order": q.question_order
        }
        for q in questions
    ]


@router.post("/start")
async def start_test(
    request: StartTestRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start test"""
    # Find registration
    registration = db.query(Registration).filter(
        Registration.duel_id == request.duel_id,
        Registration.user_id == current_user.id,
        Registration.payment_status == "completed"
    ).first()
    
    if not registration:
        raise HTTPException(status_code=404, detail="Registration not found or payment pending")
    
    # Check if attempt already exists
    existing_attempt = db.query(UserAttempt).filter(
        UserAttempt.registration_id == registration.id
    ).first()
    
    if existing_attempt:
        if existing_attempt.submitted_at:
            payload = format_submit_test_api_payload(
                existing_attempt.id,
                _attempt_total_marks_decimal(existing_attempt),
                existing_attempt.time_taken_microseconds,
                correct_answers=existing_attempt.correct_answers or 0,
                wrong_answers=existing_attempt.wrong_answers or 0,
                unanswered=existing_attempt.unanswered or 0,
            )
            payload["already_submitted"] = True
            return payload

        duel_for_existing = (
            db.query(DailyDuel).filter(DailyDuel.id == existing_attempt.duel_id).first()
        )
        return {
            "attempt_id": str(existing_attempt.id),
            "message": "Test already started",
            "time_limit_minutes": (
                duel_for_existing.time_limit_minutes if duel_for_existing else 15
            ),
        }
    
    question_count = (
        db.query(Question)
        .filter(Question.duel_id == registration.duel_id)
        .count()
    )
    duel_row = (
        db.query(DailyDuel).filter(DailyDuel.id == registration.duel_id).first()
    )
    total_questions = question_count
    if total_questions == 0 and duel_row is not None:
        total_questions = duel_row.total_questions or 0

    # Create attempt
    attempt = UserAttempt(
        id=uuid.uuid4(),
        registration_id=registration.id,
        user_id=current_user.id,
        duel_id=uuid.UUID(request.duel_id),
        language=request.language,
        started_at=None,
        total_questions=total_questions,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    limit_minutes = duel_row.time_limit_minutes if duel_row is not None else 15

    return {
        "attempt_id": str(attempt.id),
        "message": "Test started successfully",
        "time_limit_minutes": limit_minutes,
    }


@router.post("/timer-start")
async def timer_start(
    request: TimerStartRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Start (or sync) the server-side clock for an attempt.

    Call after questions are loaded so ``started_at`` does not include fetch latency.
    Idempotent: if the clock already started, returns remaining seconds from server time.
    """
    attempt_id_str = str(request.attempt_id).strip()
    try:
        attempt_uuid = uuid.UUID(attempt_id_str)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid attempt_id format: {e}",
        ) from e

    attempt = (
        db.query(UserAttempt)
        .filter(
            UserAttempt.id == attempt_uuid,
            UserAttempt.user_id == current_user.id,
        )
        .first()
    )
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")

    if attempt.submitted_at:
        payload = format_submit_test_api_payload(
            attempt.id,
            _attempt_total_marks_decimal(attempt),
            attempt.time_taken_microseconds,
            correct_answers=attempt.correct_answers or 0,
            wrong_answers=attempt.wrong_answers or 0,
            unanswered=attempt.unanswered or 0,
        )
        payload["already_submitted"] = True
        return payload

    duel_row = db.query(DailyDuel).filter(DailyDuel.id == attempt.duel_id).first()
    limit_minutes = duel_row.time_limit_minutes if duel_row is not None else 15
    limit_sec = max(1, int(limit_minutes) * 60)

    now = datetime.now(timezone.utc)
    if attempt.started_at is None:
        attempt.started_at = now
        db.commit()
        db.refresh(attempt)
        remaining = limit_sec
    else:
        elapsed = (now - attempt.started_at).total_seconds()
        remaining = max(0, int(limit_sec - elapsed))

    return {
        "message": "Timer synchronized",
        "seconds_remaining": remaining,
        "time_limit_minutes": limit_minutes,
    }


@router.post("/answer")
async def submit_answer(
    request: SubmitAnswerRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Persist or update one question response for the current attempt (upsert)."""
    reg_uuid = _parse_uuid(request.registration_id, "registration_id")
    q_uuid = _parse_uuid(request.question_id, "question_id")

    registration = db.query(Registration).filter(
        Registration.id == reg_uuid,
        Registration.user_id == current_user.id,
    ).first()

    if not registration:
        raise HTTPException(status_code=404, detail="Registration not found")

    attempt = (
        db.query(UserAttempt)
        .filter(UserAttempt.registration_id == registration.id)
        .first()
    )

    if not attempt:
        raise HTTPException(status_code=404, detail="Test not started")

    if attempt.submitted_at:
        raise HTTPException(status_code=400, detail="Test already submitted")

    question = db.query(Question).filter(Question.id == q_uuid).first()
    if not question or question.duel_id != attempt.duel_id:
        raise HTTPException(status_code=404, detail="Question not found for this duel")

    now = datetime.now(timezone.utc)
    selected = request.selected_answer

    row = (
        db.query(UserAnswer)
        .filter(
            UserAnswer.attempt_id == attempt.id,
            UserAnswer.question_id == q_uuid,
        )
        .first()
    )

    if row:
        row.selected_answer = selected
        row.answered_at = now
    else:
        db.add(
            UserAnswer(
                id=uuid.uuid4(),
                attempt_id=attempt.id,
                question_id=q_uuid,
                selected_answer=selected,
                answered_at=now,
            )
        )

    db.commit()

    return {
        "message": "Answer saved successfully",
        "question_id": request.question_id,
        "attempt_id": str(attempt.id),
    }


@router.get("/status")
async def get_test_status():
    """Get test status"""
    return {"message": "Test status endpoint"}


@router.post("/submit")
async def submit_test(
    request: SubmitTestRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit test"""
    logger.info(f"Submit test request received: attempt_id={request.attempt_id}, user_id={current_user.id}")
    
    # Validate attempt_id is provided and not empty
    if not request.attempt_id:
        logger.error("attempt_id is None")
        raise HTTPException(
            status_code=400, 
            detail="attempt_id is required and cannot be empty"
        )
    
    attempt_id_str = str(request.attempt_id).strip()
    if not attempt_id_str:
        logger.error(f"attempt_id is empty after strip: '{request.attempt_id}'")
        raise HTTPException(
            status_code=400, 
            detail="attempt_id is required and cannot be empty"
        )
    
    logger.info(f"Processing attempt_id: {attempt_id_str}")
    
    try:
        attempt_uuid = uuid.UUID(attempt_id_str)
    except ValueError as e:
        logger.error(f"Invalid UUID format: {attempt_id_str}, error: {str(e)}")
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid attempt_id format: {str(e)}. Expected UUID format. Received: '{attempt_id_str}'"
        )
    
    attempt = db.query(UserAttempt).filter(
        UserAttempt.id == attempt_uuid,
        UserAttempt.user_id == current_user.id
    ).first()
    
    if not attempt:
        logger.error(f"Attempt not found: attempt_id={attempt_id_str}, user_id={current_user.id}")
        raise HTTPException(
            status_code=404, 
            detail=f"Attempt not found for attempt_id: {attempt_id_str}"
        )

    if attempt.submitted_at:
        logger.info(
            "Idempotent submit replay: attempt_id=%s user_id=%s",
            attempt_id_str,
            current_user.id,
        )
        return format_submit_test_api_payload(
            attempt.id,
            _attempt_total_marks_decimal(attempt),
            attempt.time_taken_microseconds,
            correct_answers=attempt.correct_answers or 0,
            wrong_answers=attempt.wrong_answers or 0,
            unanswered=attempt.unanswered or 0,
        )

    questions = (
        db.query(Question)
        .filter(Question.duel_id == attempt.duel_id)
        .order_by(Question.question_order)
        .all()
    )

    answer_rows = (
        db.query(UserAnswer)
        .filter(UserAnswer.attempt_id == attempt.id)
        .all()
    )
    selections = {r.question_id: r.selected_answer for r in answer_rows}

    score_inputs = [
        QuestionScoreInput(
            question_id=q.id,
            correct_answer=q.correct_answer,
            marks=int(q.marks) if q.marks is not None else 1,
            negative_marks=Decimal(str(q.negative_marks))
            if q.negative_marks is not None
            else Decimal("0.25"),
        )
        for q in questions
    ]

    snapshot = compute_duel_attempt_score(score_inputs, selections)

    by_question = {r.question_id: r for r in answer_rows}
    for outcome in snapshot.outcomes:
        row = by_question.get(outcome.question_id)
        if row is None:
            continue
        row.is_correct = outcome.is_correct
        row.marks_obtained = outcome.marks_obtained

    submitted_at = datetime.now(timezone.utc)
    attempt.submitted_at = submitted_at
    attempt.total_marks = snapshot.total_marks
    attempt.correct_answers = snapshot.correct_answers
    attempt.wrong_answers = snapshot.wrong_answers
    attempt.unanswered = snapshot.unanswered

    if attempt.started_at:
        time_diff = submitted_at - attempt.started_at
        attempt.time_taken_microseconds = int(time_diff.total_seconds() * 1_000_000)
    else:
        attempt.time_taken_microseconds = 0

    db.commit()
    logger.info(f"Test submitted successfully: attempt_id={attempt_id_str}")

    return format_submit_test_api_payload(
        attempt.id,
        snapshot.total_marks,
        attempt.time_taken_microseconds,
        correct_answers=snapshot.correct_answers,
        wrong_answers=snapshot.wrong_answers,
        unanswered=snapshot.unanswered,
    )

