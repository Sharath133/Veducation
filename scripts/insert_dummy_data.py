"""
Script to insert dummy data for UI testing
"""
import sys
import os
from datetime import date, datetime, timezone
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models.duel import DailyDuel, Registration
from app.models.question import Question
from app.models.user import User
import uuid

def insert_dummy_data():
    """Insert dummy data for testing"""
    db: Session = SessionLocal()
    
    try:
        # Get or create a test user
        user = db.query(User).filter(User.mobile_number == "9347485455").first()
        if not user:
            print("User not found. Please login first to create user.")
            return
        
        # Create today's duel
        today = date.today().strftime("%Y-%m-%d")
        existing_duel = db.query(DailyDuel).filter(DailyDuel.duel_date == today).first()
        
        if existing_duel:
            print(f"Duel for {today} already exists. Skipping creation.")
            duel_id = existing_duel.id
        else:
            duel = DailyDuel(
                id=uuid.uuid4(),
                duel_date=today,
                total_questions=15,
                time_limit_minutes=15,
                registration_fee=Decimal("5.00"),
                prize_pool=Decimal("1000.00"),
                status="upcoming"
            )
            db.add(duel)
            db.commit()
            db.refresh(duel)
            duel_id = duel.id
            print(f"Created duel for {today} with ID: {duel_id}")
        
        # Create dummy questions
        existing_questions = db.query(Question).filter(Question.duel_id == duel_id).count()
        
        if existing_questions == 0:
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
                    "correct_answer": "B"
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
                    "correct_answer": "B"
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
                    "correct_answer": "B"
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
                    "correct_answer": "A"
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
                    "correct_answer": "A"
                }
            ]
            
            for idx, q_data in enumerate(questions_data, start=1):
                question = Question(
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
                    question_order=idx
                )
                db.add(question)
            
            db.commit()
            print(f"Created {len(questions_data)} questions for duel")
        else:
            print(f"Questions already exist for this duel ({existing_questions} questions)")
        
        print("\n✅ Dummy data inserted successfully!")
        print(f"   Duel ID: {duel_id}")
        print(f"   Date: {today}")
        print(f"   Questions: {existing_questions or len(questions_data)}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error inserting dummy data: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    insert_dummy_data()
