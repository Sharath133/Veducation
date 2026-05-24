"""
User feedback / suggestions model
"""
import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Uuid
from sqlalchemy.sql import func

from app.database import Base


class UserFeedback(Base):
    """User feedback or product suggestion"""

    __tablename__ = "user_feedback"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, default="suggestion", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
