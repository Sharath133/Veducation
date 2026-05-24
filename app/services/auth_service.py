"""
Authentication Service
"""
from sqlalchemy.orm import Session
from app.models.user import User, OTPVerification
from app.services.otp_service import OTPService
from app.utils.security import create_access_token, create_refresh_token
from app.utils.helpers import generate_otp
from app.utils.validators import generate_referral_code
from app.config import settings
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

TEST_OTP_CODE = "333333"


class AuthService:
    """Authentication service"""
    
    def __init__(self, db: Session):
        self.db = db
        self.otp_service = OTPService()
    
    async def send_otp(self, mobile_number: str, purpose: str) -> dict:
        """Send OTP to mobile number"""
        # Validate mobile number
        from app.utils.validators import validate_mobile_number
        if not validate_mobile_number(mobile_number):
            raise ValueError("Invalid mobile number")
        
        # Generate OTP
        # otp_code = generate_otp(settings.OTP_LENGTH)
        otp_code = TEST_OTP_CODE
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
        
        # Save OTP to database
        otp_record = OTPVerification(
            mobile_number=mobile_number,
            otp_code=otp_code,
            purpose=purpose,
            expires_at=expires_at
        )
        self.db.add(otp_record)
        self.db.commit()
        
        # Send OTP via SMS
        try:
            await self.otp_service.send_otp(mobile_number, otp_code)
            logger.info(f"OTP sent to {mobile_number}")
        except Exception as e:
            logger.error(f"Failed to send OTP: {e}")
            raise
        
        return {"message": "OTP sent successfully", "expires_in_minutes": settings.OTP_EXPIRE_MINUTES}
    
    async def verify_otp(self, mobile_number: str, otp_code: str) -> dict:
        """Verify OTP and return tokens"""
        # Get latest OTP record
        otp_record = self.db.query(OTPVerification).filter(
            OTPVerification.mobile_number == mobile_number,
            OTPVerification.otp_code == otp_code,
            OTPVerification.is_verified == False
        ).order_by(OTPVerification.created_at.desc()).first()
        
        if not otp_record:
            raise ValueError("Invalid OTP")
        
        # Check expiration
        if datetime.now(timezone.utc) > otp_record.expires_at:
            raise ValueError("OTP expired")
        
        # Mark OTP as verified
        otp_record.is_verified = True
        self.db.commit()
        
        # Get or create user
        user = self.db.query(User).filter(User.mobile_number == mobile_number).first()
        if not user:
            # Create new user
            referral_code = generate_referral_code(mobile_number)
            user = User(
                mobile_number=mobile_number,
                referral_code=referral_code
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        
        # Generate tokens
        access_token = create_access_token({"sub": str(user.id)})
        refresh_token = create_refresh_token({"sub": str(user.id)})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    async def refresh_token(self, refresh_token: str) -> dict:
        """Refresh access token"""
        from app.utils.security import verify_token
        
        payload = verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise ValueError("Invalid refresh token")
        
        user_id = payload.get("sub")
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        # Generate new access token
        access_token = create_access_token({"sub": str(user.id)})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    async def send_mobile_change_otp(self, user: User, new_mobile_number: str) -> dict:
        """Send OTP to a new mobile number for an authenticated user (mobile change)."""
        from app.utils.validators import validate_mobile_number

        if not validate_mobile_number(new_mobile_number):
            raise ValueError("Invalid mobile number")
        if new_mobile_number == user.mobile_number:
            raise ValueError("New number must be different from your current mobile number")

        taken = self.db.query(User).filter(User.mobile_number == new_mobile_number).first()
        if taken:
            raise ValueError("This mobile number is already registered")

        # otp_code = generate_otp(settings.OTP_LENGTH)
        otp_code = TEST_OTP_CODE
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

        otp_record = OTPVerification(
            mobile_number=new_mobile_number,
            otp_code=otp_code,
            purpose="mobile_change",
            expires_at=expires_at,
        )
        self.db.add(otp_record)
        self.db.commit()

        try:
            await self.otp_service.send_otp(new_mobile_number, otp_code)
            logger.info("Mobile-change OTP sent to %s", new_mobile_number)
        except Exception as e:
            logger.error("Failed to send mobile-change OTP: %s", e)
            raise

        return {"message": "OTP sent successfully", "expires_in_minutes": settings.OTP_EXPIRE_MINUTES}

    async def verify_mobile_change(self, user: User, new_mobile_number: str, otp_code: str) -> User:
        """Verify OTP and assign the new mobile number to the current user."""
        from app.utils.validators import validate_mobile_number

        if not validate_mobile_number(new_mobile_number):
            raise ValueError("Invalid mobile number")

        otp_record = (
            self.db.query(OTPVerification)
            .filter(
                OTPVerification.mobile_number == new_mobile_number,
                OTPVerification.purpose == "mobile_change",
                OTPVerification.otp_code == otp_code,
                OTPVerification.is_verified == False,  # noqa: E712
            )
            .order_by(OTPVerification.created_at.desc())
            .first()
        )

        if not otp_record:
            raise ValueError("Invalid OTP")

        if datetime.now(timezone.utc) > otp_record.expires_at:
            raise ValueError("OTP expired")

        taken = (
            self.db.query(User)
            .filter(User.mobile_number == new_mobile_number, User.id != user.id)
            .first()
        )
        if taken:
            raise ValueError("This mobile number is already registered")

        otp_record.is_verified = True
        user.mobile_number = new_mobile_number
        self.db.commit()
        self.db.refresh(user)
        return user

