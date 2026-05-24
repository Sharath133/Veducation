"""
User Models
"""
from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Text, Uuid
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mobile_number = Column(String(15), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    upi_mobile = Column(String(15), nullable=True)
    # RazorpayX fund account id for automated payouts (set via secure ops / future KYC flow)
    razorpay_fund_account_id = Column(String(255), nullable=True)
    referral_code = Column(String(20), unique=True, nullable=False, index=True)
    referred_by_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    loyalty_points = Column(Integer, default=0)
    free_duel_entry_credits = Column(Integer, default=0, nullable=False, server_default="0")
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False, index=True)  # Admin flag
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    referred_by = relationship("User", remote_side=[id])
    registrations = relationship("Registration", back_populates="user")
    attempts = relationship("UserAttempt", back_populates="user")
    referrals = relationship("Referral", foreign_keys="Referral.referrer_id", back_populates="referrer")
    loyalty_transactions = relationship("LoyaltyTransaction", back_populates="user")


class OTPVerification(Base):
    """OTP Verification model"""
    __tablename__ = "otp_verifications"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mobile_number = Column(String(15), nullable=False, index=True)
    otp_code = Column(String(6), nullable=False)
    purpose = Column(String(20), nullable=False)  # login, registration
    is_verified = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

