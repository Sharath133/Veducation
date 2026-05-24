"""
Payment Models
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Numeric
from sqlalchemy import Uuid
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Payment(Base):
    """Payment model"""
    __tablename__ = "payments"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    registration_id = Column(Uuid(as_uuid=True), ForeignKey("registrations.id"), nullable=False)
    razorpay_order_id = Column(String(255), nullable=True)
    razorpay_payment_id = Column(String(255), nullable=True)
    razorpay_signature = Column(String(255), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), default="pending")  # pending, completed, failed, refunded
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Reward(Base):
    """Reward model"""
    __tablename__ = "rewards_history"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    attempt_id = Column(Uuid(as_uuid=True), ForeignKey("user_attempts.id"), nullable=False)
    duel_id = Column(Uuid(as_uuid=True), ForeignKey("daily_duels.id"), nullable=False, index=True)
    rank = Column(Integer, nullable=False)
    reward_amount = Column(Numeric(10, 2), nullable=False)
    payment_transaction_id = Column(String(255), nullable=True)
    payment_status = Column(String(20), default="pending")  # pending, processed, paid
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

