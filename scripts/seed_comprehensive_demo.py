"""
Seed comprehensive demo data for local / Docker testing.

Creates:
  - Demo users (admin + students) with valid Indian mobile numbers
  - Today's daily duel (active) + 5 bilingual MCQs
  - Paid registration + payment for the primary student
  - PYQ pack + sample PYQ questions
  - Referral + loyalty transaction
  - Support ticket + user feedback (admin inbox testing)
  - Admin inbox message for a student

Run inside backend container (from repo / app root is /app):
  docker exec veducation_backend python scripts/seed_comprehensive_demo.py

Optional — remove today's duel and ALL related rows first (dev only):
  docker exec veducation_backend python scripts/seed_comprehensive_demo.py --wipe-today-duel

Environment:
  DATABASE_URL must point at the same DB the API uses (Docker Compose sets this).
"""
from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models.admin_user_message import AdminUserMessage  # noqa: E402
from app.models.duel import DailyDuel, Registration  # noqa: E402
from app.models.leaderboard import UserAnswer, UserAttempt  # noqa: E402
from app.models.payment import Payment, Reward  # noqa: E402
from app.models.question import Question  # noqa: E402
from app.models.pyq import PYQ, PYQQuestion  # noqa: E402
from app.models.referral import LoyaltyTransaction, Referral  # noqa: E402
from app.models.settlement import DuelSettlement, SettlementPayout  # noqa: E402
from app.models.support_ticket import SupportTicket  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.user_feedback import UserFeedback  # noqa: E402
from app.utils.validators import generate_referral_code  # noqa: E402

# Valid Indian mobiles: ^[6-9]\d{9}$
DEMO_ADMIN_MOBILE = "9876500001"
DEMO_STUDENT_MOBILE = "9876500002"
DEMO_STUDENT2_MOBILE = "9876500003"


def _wipe_today_duel(db: Session) -> bool:
    """Delete today's duel and dependent rows. Returns True if a duel was removed."""
    today = date.today().strftime("%Y-%m-%d")
    duel = db.query(DailyDuel).filter(DailyDuel.duel_date == today).first()
    if not duel:
        print(f"No duel found for {today}; nothing to wipe.")
        return False

    duel_id = duel.id
    attempt_ids = [a.id for a in db.query(UserAttempt).filter(UserAttempt.duel_id == duel_id).all()]
    reg_ids = [r.id for r in db.query(Registration).filter(Registration.duel_id == duel_id).all()]

    if attempt_ids:
        db.query(UserAnswer).filter(UserAnswer.attempt_id.in_(attempt_ids)).delete(
            synchronize_session=False
        )
        db.query(SettlementPayout).filter(SettlementPayout.attempt_id.in_(attempt_ids)).delete(
            synchronize_session=False
        )
        db.query(Reward).filter(Reward.attempt_id.in_(attempt_ids)).delete(synchronize_session=False)

    db.query(DuelSettlement).filter(DuelSettlement.duel_id == duel_id).delete(synchronize_session=False)
    db.query(UserAttempt).filter(UserAttempt.duel_id == duel_id).delete(synchronize_session=False)

    if reg_ids:
        db.query(Payment).filter(Payment.registration_id.in_(reg_ids)).delete(synchronize_session=False)
        db.query(Registration).filter(Registration.id.in_(reg_ids)).delete(synchronize_session=False)

    db.query(Question).filter(Question.duel_id == duel_id).delete(synchronize_session=False)
    db.delete(duel)
    db.commit()
    print(f"Wiped duel {duel_id} for {today} and related rows.")
    return True


def _get_or_create_user(
    db: Session,
    mobile: str,
    *,
    name: str | None,
    is_admin: bool = False,
    loyalty_points: int = 0,
    referred_by: User | None = None,
    upi_mobile: str | None = None,
) -> User:
    user = db.query(User).filter(User.mobile_number == mobile).first()
    if user:
        user.name = name or user.name
        user.is_admin = is_admin
        user.loyalty_points = loyalty_points
        user.upi_mobile = upi_mobile or user.upi_mobile
        if referred_by and not user.referred_by_id:
            user.referred_by_id = referred_by.id
        db.commit()
        db.refresh(user)
        print(f"Updated user {mobile} (id={user.id})")
        return user

    ref = generate_referral_code(mobile)
    user = User(
        id=uuid.uuid4(),
        mobile_number=mobile,
        referral_code=ref,
        name=name,
        is_admin=is_admin,
        loyalty_points=loyalty_points,
        upi_mobile=upi_mobile,
        referred_by_id=referred_by.id if referred_by else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"Created user {mobile} (id={user.id}, referral={ref})")
    return user


def _seed_questions_for_duel(db: Session, duel_id: uuid.UUID) -> int:
    count = db.query(Question).filter(Question.duel_id == duel_id).count()
    if count > 0:
        print(f"Duel already has {count} questions; skipping question seed.")
        return count

    questions_data = [
        {
            "question_text_en": "What is the capital of India?",
            "question_text_te": "భారతదేశ రాజధాని ఏది?",
            "option_a_en": "Mumbai",
            "option_a_te": "ముంబై",
            "option_b_en": "Delhi",
            "option_b_te": "ఢిల్లీ",
            "option_c_en": "Kolkata",
            "option_c_te": "కోల్కతా",
            "option_d_en": "Chennai",
            "option_d_te": "చెన్నై",
            "correct_answer": "B",
        },
        {
            "question_text_en": "Which is the largest planet in our solar system?",
            "question_text_te": "మన సౌర వ్యవస్థలో అతిపెద్ద గ్రహం ఏది?",
            "option_a_en": "Earth",
            "option_a_te": "భూమి",
            "option_b_en": "Jupiter",
            "option_b_te": "గురుడు",
            "option_c_en": "Saturn",
            "option_c_te": "శని",
            "option_d_en": "Neptune",
            "option_d_te": "నెప్ట్యూన్",
            "correct_answer": "B",
        },
        {
            "question_text_en": "What is 2 + 2?",
            "question_text_te": "2 + 2 ఎంత?",
            "option_a_en": "3",
            "option_a_te": "3",
            "option_b_en": "4",
            "option_b_te": "4",
            "option_c_en": "5",
            "option_c_te": "5",
            "option_d_en": "6",
            "option_d_te": "6",
            "correct_answer": "B",
        },
        {
            "question_text_en": "Who wrote the Indian National Anthem?",
            "question_text_te": "భారత జాతీయ గీతాన్ని ఎవరు రాశారు?",
            "option_a_en": "Rabindranath Tagore",
            "option_a_te": "రవీంద్రనాథ్ టాగోర్",
            "option_b_en": "Mahatma Gandhi",
            "option_b_te": "మహాత్మా గాంధీ",
            "option_c_en": "Jawaharlal Nehru",
            "option_c_te": "జవహర్లాల్ నెహ్రూ",
            "option_d_en": "Subhash Chandra Bose",
            "option_d_te": "సుభాష్ చంద్రబోస్",
            "correct_answer": "A",
        },
        {
            "question_text_en": "What is the chemical symbol for water?",
            "question_text_te": "నీటి రసాయన సంకేతం ఏది?",
            "option_a_en": "H2O",
            "option_a_te": "H2O",
            "option_b_en": "CO2",
            "option_b_te": "CO2",
            "option_c_en": "O2",
            "option_c_te": "O2",
            "option_d_en": "NaCl",
            "option_d_te": "NaCl",
            "correct_answer": "A",
        },
    ]

    for idx, q_data in enumerate(questions_data, start=1):
        q = Question(
            id=uuid.uuid4(),
            duel_id=duel_id,
            question_text_en=q_data["question_text_en"],
            question_text_te=q_data["question_text_te"],
            option_a_en=q_data["option_a_en"],
            option_a_te=q_data["option_a_te"],
            option_b_en=q_data["option_b_en"],
            option_b_te=q_data["option_b_te"],
            option_c_en=q_data["option_c_en"],
            option_c_te=q_data["option_c_te"],
            option_d_en=q_data["option_d_en"],
            option_d_te=q_data["option_d_te"],
            correct_answer=q_data["correct_answer"],
            marks=1,
            negative_marks=Decimal("0.25"),
            question_order=idx,
        )
        db.add(q)
    db.commit()
    print(f"Inserted {len(questions_data)} questions for duel {duel_id}")
    return len(questions_data)


def _seed_today_duel(db: Session) -> DailyDuel:
    today = date.today().strftime("%Y-%m-%d")
    duel = db.query(DailyDuel).filter(DailyDuel.duel_date == today).first()
    if duel:
        n = _seed_questions_for_duel(db, duel.id)
        if duel.total_questions != n and n > 0:
            duel.total_questions = n
            duel.time_limit_minutes = max(duel.time_limit_minutes, n)
            db.commit()
            db.refresh(duel)
        print(f"Using existing duel for {today} (id={duel.id})")
        return duel

    duel = DailyDuel(
        id=uuid.uuid4(),
        duel_date=today,
        total_questions=5,
        time_limit_minutes=5,
        registration_fee=Decimal("9.00"),
        prize_pool=Decimal("5000.00"),
        status="active",
    )
    db.add(duel)
    db.commit()
    db.refresh(duel)
    _seed_questions_for_duel(db, duel.id)
    print(f"Created duel for {today} (id={duel.id})")
    return duel


def _seed_registration_and_payment(db: Session, user: User, duel: DailyDuel) -> Registration:
    existing = (
        db.query(Registration)
        .filter(Registration.user_id == user.id, Registration.duel_id == duel.id)
        .first()
    )
    if existing:
        if existing.payment_status != "completed":
            existing.payment_status = "completed"
            existing.payment_amount = duel.registration_fee
            db.commit()
            db.refresh(existing)
            print(f"Updated registration {existing.id} to payment completed")
        else:
            print(f"Registration already complete for {user.mobile_number}")
        pay = db.query(Payment).filter(Payment.registration_id == existing.id).first()
        if not pay:
            pay = Payment(
                id=uuid.uuid4(),
                registration_id=existing.id,
                amount=duel.registration_fee,
                status="completed",
            )
            db.add(pay)
            db.commit()
        return existing

    reg = Registration(
        id=uuid.uuid4(),
        user_id=user.id,
        duel_id=duel.id,
        payment_status="completed",
        payment_amount=duel.registration_fee,
    )
    db.add(reg)
    db.commit()
    db.refresh(reg)

    pay = Payment(
        id=uuid.uuid4(),
        registration_id=reg.id,
        amount=duel.registration_fee,
        status="completed",
    )
    db.add(pay)
    db.commit()
    print(f"Created registration {reg.id} + payment for {user.mobile_number}")
    return reg


def _seed_pyq_pack(db: Session) -> None:
    title = "Demo PYQ Pack (seeded)"
    pyq = db.query(PYQ).filter(PYQ.title == title).first()
    if not pyq:
        pyq = PYQ(
            id=uuid.uuid4(),
            title=title,
            year=2024,
            month="April",
            subject="General",
            difficulty="Easy",
            total_questions=0,
            is_active=True,
        )
        db.add(pyq)
        db.commit()
        db.refresh(pyq)
        print(f"Created PYQ {pyq.id}")

    n = db.query(PYQQuestion).filter(PYQQuestion.pyq_id == pyq.id).count()
    if n > 0:
        print(f"PYQ already has {n} questions; skipping PYQ questions.")
        return

    sample = [
        (
            "PYQ Q1: Choose the smallest prime.",
            "PYQ Q1: చిన్న ప్రధాన సంఖ్య ఏది?",
            "0",
            "0",
            "1",
            "1",
            "2",
            "2",
            "4",
            "4",
            "C",
        ),
        (
            "PYQ Q2: Speed of light is fastest in?",
            "PYQ Q2: కాంతి వేగం ఎక్కడ అత్యధికం?",
            "Water",
            "నీరు",
            "Vacuum",
            "శూన్యం",
            "Glass",
            "గాజు",
            "Air",
            "గాలి",
            "B",
        ),
    ]
    for i, row in enumerate(sample, start=1):
        q = PYQQuestion(
            id=uuid.uuid4(),
            pyq_id=pyq.id,
            question_text_en=row[0],
            question_text_te=row[1],
            option_a_en=row[2],
            option_a_te=row[3],
            option_b_en=row[4],
            option_b_te=row[5],
            option_c_en=row[6],
            option_c_te=row[7],
            option_d_en=row[8],
            option_d_te=row[9],
            correct_answer=row[10],
            marks=1,
            negative_marks=Decimal("0.25"),
            question_order=i,
        )
        db.add(q)
    pyq.total_questions = len(sample)
    db.commit()
    print(f"Added {len(sample)} PYQ questions to pack {pyq.id}")


def _seed_support_and_feedback(db: Session, student: User, student2: User, admin: User) -> None:
    if not db.query(SupportTicket).filter(SupportTicket.user_id == student.id).first():
        db.add(
            SupportTicket(
                id=uuid.uuid4(),
                user_id=student.id,
                subject="Demo ticket: payment receipt",
                body="This is seeded data to test the admin support inbox.",
                status="open",
            )
        )
        print("Added demo support ticket")

    if not db.query(UserFeedback).filter(UserFeedback.user_id == student2.id).first():
        db.add(
            UserFeedback(
                id=uuid.uuid4(),
                user_id=student2.id,
                title="Demo feedback",
                body="Seeded suggestion to test admin feedback list.",
                category="suggestion",
            )
        )
        print("Added demo user feedback")

    if not db.query(AdminUserMessage).filter(AdminUserMessage.user_id == student.id).first():
        db.add(
            AdminUserMessage(
                id=uuid.uuid4(),
                user_id=student.id,
                title="Welcome from V Education (demo)",
                body="This message was inserted by seed_comprehensive_demo.py for inbox testing.",
                created_by_admin_id=admin.id,
            )
        )
        print("Added demo admin message for student")
    db.commit()


def _seed_referral_and_loyalty(db: Session, referrer: User, referred: User) -> None:
    if not db.query(Referral).filter(Referral.referred_id == referred.id).first():
        db.add(
            Referral(
                id=uuid.uuid4(),
                referrer_id=referrer.id,
                referred_id=referred.id,
                points_awarded=10,
            )
        )
        print("Added demo referral row")

    if not db.query(LoyaltyTransaction).filter(LoyaltyTransaction.user_id == referrer.id).first():
        db.add(
            LoyaltyTransaction(
                id=uuid.uuid4(),
                user_id=referrer.id,
                transaction_type="earned",
                points=10,
                description="Demo: referral bonus (seed)",
            )
        )
        print("Added demo loyalty transaction for referrer")
    db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed comprehensive demo data")
    parser.add_argument(
        "--wipe-today-duel",
        action="store_true",
        help="Delete today's duel and all related attempts/registrations/questions first (dev only).",
    )
    args = parser.parse_args()

    db: Session = SessionLocal()
    try:
        if args.wipe_today_duel:
            _wipe_today_duel(db)

        admin = _get_or_create_user(
            db,
            DEMO_ADMIN_MOBILE,
            name="Demo Admin",
            is_admin=True,
            loyalty_points=40,
            upi_mobile=DEMO_ADMIN_MOBILE,
        )
        student = _get_or_create_user(
            db,
            DEMO_STUDENT_MOBILE,
            name="Demo Student",
            is_admin=False,
            loyalty_points=20,
            referred_by=admin,
            upi_mobile=DEMO_STUDENT_MOBILE,
        )
        student2 = _get_or_create_user(
            db,
            DEMO_STUDENT2_MOBILE,
            name="Demo Student Two",
            is_admin=False,
            loyalty_points=0,
            upi_mobile=DEMO_STUDENT2_MOBILE,
        )

        duel = _seed_today_duel(db)
        _seed_registration_and_payment(db, student, duel)
        _seed_pyq_pack(db)
        _seed_support_and_feedback(db, student, student2, admin)
        _seed_referral_and_loyalty(db, admin, student)

        print("\n=== Demo seed complete ===")
        print("Accounts (OTP: check backend logs when SMS_PROVIDER is not msg91/twilio):")
        print(f"  Admin:   {DEMO_ADMIN_MOBILE}  (is_admin=true)")
        print(f"  Student: {DEMO_STUDENT_MOBILE}  (registered + paid for today's duel)")
        print(f"  Extra:   {DEMO_STUDENT2_MOBILE}")
        print(f"Today's duel id: {duel.id}")
        print("Admin portal (Flutter web): http://localhost:<port>/#/admin/login")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
