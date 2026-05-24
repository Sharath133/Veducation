"""
Leaderboard Models
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Numeric, BigInteger, Boolean
from sqlalchemy import Uuid
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class UserAttempt(Base):
    """User Attempt model"""
    __tablename__ = "user_attempts"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    registration_id = Column(Uuid(as_uuid=True), ForeignKey("registrations.id"), nullable=False, index=True)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    duel_id = Column(Uuid(as_uuid=True), ForeignKey("daily_duels.id"), nullable=False, index=True)
    
    language = Column(String(10), nullable=False)  # 'en' or 'te'
    started_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    time_taken_microseconds = Column(BigInteger, nullable=True)  # Total time in microseconds
    total_marks = Column(Numeric(10, 2), default=0)
    total_questions = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    wrong_answers = Column(Integer, default=0)
    unanswered = Column(Integer, default=0)
    rank = Column(Integer, nullable=True, index=True)
    reward_amount = Column(Numeric(10, 2), default=0)
    reward_status = Column(String(20), default="pending", index=True)  # pending, processed, paid
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    registration = relationship("Registration", back_populates="attempt")
    user = relationship("User", back_populates="attempts")
    duel = relationship("DailyDuel", back_populates="attempts")
    answers = relationship("UserAnswer", back_populates="attempt")


class UserAnswer(Base):
    """User Answer model"""
    __tablename__ = "user_answers"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id = Column(Uuid(as_uuid=True), ForeignKey("user_attempts.id"), nullable=False, index=True)
    question_id = Column(Uuid(as_uuid=True), ForeignKey("questions.id"), nullable=False, index=True)
    selected_answer = Column(String(1), nullable=True)  # A, B, C, D, or NULL
    is_correct = Column(Boolean, nullable=True)
    marks_obtained = Column(Numeric(5, 2), default=0)
    answered_at = Column(DateTime(timezone=True), nullable=True)
    time_taken_microseconds = Column(BigInteger, nullable=True)  # Time taken for this question
    
    # Relationships
    attempt = relationship("UserAttempt", back_populates="answers")
    question = relationship("Question", back_populates="answers")

