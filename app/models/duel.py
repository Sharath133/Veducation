"""
Duel Models
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Numeric, Enum as SQLEnum, UniqueConstraint, Uuid
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import date
from app.database import Base


class DailyDuel(Base):
    """Daily Duel model"""
    __tablename__ = "daily_duels"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    duel_date = Column(String, unique=True, nullable=False, index=True)  # Format: YYYY-MM-DD
    total_questions = Column(Integer, default=15)
    time_limit_minutes = Column(Integer, default=15)
    registration_fee = Column(Numeric(10, 2), nullable=False)
    prize_pool = Column(Numeric(10, 2), default=0)
    status = Column(String(20), default="upcoming", index=True)  # upcoming, active, completed, settled
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    registrations = relationship("Registration", back_populates="duel")
    questions = relationship("Question", back_populates="duel")
    attempts = relationship("UserAttempt", back_populates="duel")


class Registration(Base):
    """Registration model"""
    __tablename__ = "registrations"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    duel_id = Column(Uuid(as_uuid=True), ForeignKey("daily_duels.id"), nullable=False, index=True)
    payment_id = Column(String(255), nullable=True)
    payment_status = Column(String(20), default="pending", index=True)  # pending, completed, failed, refunded
    payment_amount = Column(Numeric(10, 2), nullable=True)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="registrations")
    duel = relationship("DailyDuel", back_populates="registrations")
    attempt = relationship("UserAttempt", back_populates="registration", uselist=False)
    
    __table_args__ = (
        UniqueConstraint('user_id', 'duel_id', name='unique_user_duel_registration'),
    )

