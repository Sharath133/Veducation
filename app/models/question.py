"""
Question Models
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Numeric
from sqlalchemy import Uuid
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Question(Base):
    """Question model"""
    __tablename__ = "questions"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    duel_id = Column(Uuid(as_uuid=True), ForeignKey("daily_duels.id"), nullable=False, index=True)
    
    # Bilingual question text
    question_text_en = Column(Text, nullable=False)
    question_text_te = Column(Text, nullable=False)
    
    # Bilingual options
    option_a_en = Column(Text, nullable=False)
    option_a_te = Column(Text, nullable=False)
    option_b_en = Column(Text, nullable=False)
    option_b_te = Column(Text, nullable=False)
    option_c_en = Column(Text, nullable=False)
    option_c_te = Column(Text, nullable=False)
    option_d_en = Column(Text, nullable=False)
    option_d_te = Column(Text, nullable=False)
    
    correct_answer = Column(String(1), nullable=False)  # A, B, C, or D
    marks = Column(Integer, default=1)
    negative_marks = Column(Numeric(3, 2), default=0.25)
    question_order = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    duel = relationship("DailyDuel", back_populates="questions")
    answers = relationship("UserAnswer", back_populates="question")

