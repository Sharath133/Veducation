"""
Script to create an admin user
Usage: python scripts/create_admin.py <mobile_number>
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User
from app.utils.validators import generate_referral_code

def create_admin(mobile_number: str):
    """Create an admin user"""
    db: Session = SessionLocal()
    try:
        # Check if user already exists
        user = db.query(User).filter(User.mobile_number == mobile_number).first()
        
        if user:
            # Make existing user an admin
            user.is_admin = True
            user.is_active = True
            db.commit()
            print(f"✓ User {mobile_number} is now an admin")
        else:
            # Create new admin user
            referral_code = generate_referral_code(mobile_number)
            admin_user = User(
                mobile_number=mobile_number,
                referral_code=referral_code,
                is_admin=True,
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print(f"✓ Admin user created: {mobile_number}")
            print(f"  User ID: {admin_user.id}")
            print(f"  Referral Code: {admin_user.referral_code}")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error creating admin: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/create_admin.py <mobile_number>")
        print("Example: python scripts/create_admin.py 9876543210")
        sys.exit(1)
    
    mobile_number = sys.argv[1]
    create_admin(mobile_number)
