"""
Support ticket model
"""
import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Uuid
from sqlalchemy.sql import func

from app.database import Base


class SupportTicket(Base):
    """User-submitted support ticket"""

    __tablename__ = "support_tickets"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(
        String(32),
        nullable=False,
        default="open",
        index=True,
    )  # open, in_progress, resolved, closed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
