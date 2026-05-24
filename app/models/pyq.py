"""
PYQ (Previous Year Questions) Models
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Numeric, Boolean, Uuid
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class PYQ(Base):
    """Previous Year Question Paper model"""
    __tablename__ = "pyqs"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    year = Column(Integer, nullable=False, index=True)
    month = Column(String(20), nullable=True)  # January, February, etc.
    subject = Column(String(100), nullable=True)
    difficulty = Column(String(20), default="Medium")  # Easy, Medium, Hard
    total_questions = Column(Integer, default=0)
    reference_pdf_path = Column(String(512), nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    questions = relationship("PYQQuestion", back_populates="pyq", cascade="all, delete-orphan")


class PYQQuestion(Base):
    """PYQ Question model"""
    __tablename__ = "pyq_questions"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pyq_id = Column(Uuid(as_uuid=True), ForeignKey("pyqs.id"), nullable=False, index=True)
    
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
    explanation_en = Column(Text, nullable=True)
    explanation_te = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    pyq = relationship("PYQ", back_populates="questions")


class PYQCategory(Base):
    """Top-level PYQ category shown on the student PYQ screen."""
    __tablename__ = "pyq_categories"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), nullable=False, unique=True, index=True)
    title = Column(String(120), nullable=False)
    icon = Column(String(50), nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    sections = relationship(
        "PYQSection",
        back_populates="category",
        cascade="all, delete-orphan",
    )


class PYQSection(Base):
    """Editable section under a PYQ category, such as Prelims or APPSC."""
    __tablename__ = "pyq_sections"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(Uuid(as_uuid=True), ForeignKey("pyq_categories.id"), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    category = relationship("PYQCategory", back_populates="sections")
    pdfs = relationship(
        "PYQSectionPDF",
        back_populates="section",
        cascade="all, delete-orphan",
    )


class PYQSectionPDF(Base):
    """PDF uploaded under a PYQ section."""
    __tablename__ = "pyq_section_pdfs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    section_id = Column(Uuid(as_uuid=True), ForeignKey("pyq_sections.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    file_path = Column(String(512), nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    section = relationship("PYQSection", back_populates="pdfs")
