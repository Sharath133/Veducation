"""
Script to cleanup dummy data after testing
"""
import sys
import os
from datetime import date

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.duel import DailyDuel, Registration
from app.models.question import Question
from app.models.leaderboard import UserAttempt, UserAnswer
from app.models.payment import Payment

def cleanup_dummy_data():
    """Cleanup dummy data created for testing"""
    db: Session = SessionLocal()
    
    try:
        today = date.today().strftime("%Y-%m-%d")
        
        # Find today's duel
        duel = db.query(DailyDuel).filter(DailyDuel.duel_date == today).first()
        
        if not duel:
            print(f"No duel found for {today}. Nothing to cleanup.")
            return
        
        duel_id = duel.id
        print(f"Found duel for {today} (ID: {duel_id})")
        
        # Delete related data
        deleted_count = 0
        
        # Delete user answers
        answers_count = db.query(UserAnswer).join(Question).filter(
            Question.duel_id == duel_id
        ).delete(synchronize_session=False)
        deleted_count += answers_count
        print(f"Deleted {answers_count} user answers")
        
        # Delete user attempts
        attempts_count = db.query(UserAttempt).filter(
            UserAttempt.duel_id == duel_id
        ).delete(synchronize_session=False)
        deleted_count += attempts_count
        print(f"Deleted {attempts_count} user attempts")

        reg_ids = [r.id for r in db.query(Registration).filter(Registration.duel_id == duel_id).all()]
        if reg_ids:
            payments_count = db.query(Payment).filter(Payment.registration_id.in_(reg_ids)).delete(
                synchronize_session=False
            )
            deleted_count += payments_count
            print(f"Deleted {payments_count} payments")

        # Delete registrations
        registrations_count = db.query(Registration).filter(
            Registration.duel_id == duel_id
        ).delete(synchronize_session=False)
        deleted_count += registrations_count
        print(f"Deleted {registrations_count} registrations")
        
        # Delete questions
        questions_count = db.query(Question).filter(
            Question.duel_id == duel_id
        ).delete(synchronize_session=False)
        deleted_count += questions_count
        print(f"Deleted {questions_count} questions")
        
        # Delete the duel
        db.delete(duel)
        db.commit()
        deleted_count += 1
        print(f"Deleted duel")
        
        print(f"\n✅ Cleanup completed successfully!")
        print(f"   Total items deleted: {deleted_count}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error cleaning up dummy data: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    response = input("Are you sure you want to delete all dummy data for today? (yes/no): ")
    if response.lower() == "yes":
        cleanup_dummy_data()
    else:
        print("Cleanup cancelled.")
