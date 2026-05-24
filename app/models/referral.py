"""
Referral Models
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Uuid
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Referral(Base):
    """Referral model"""
    __tablename__ = "referrals"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    referrer_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    referred_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    points_awarded = Column(Integer, default=10)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    referrer = relationship("User", foreign_keys=[referrer_id], back_populates="referrals")
    referred = relationship("User", foreign_keys=[referred_id])


class LoyaltyTransaction(Base):
    """Loyalty Points Transaction model"""
    __tablename__ = "loyalty_transactions"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    transaction_type = Column(String(20), nullable=False, index=True)  # earned, redeemed, expired
    points = Column(Integer, nullable=False)
    reference_id = Column(Uuid(as_uuid=True), nullable=True)  # Can reference referral or registration
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="loyalty_transactions")

