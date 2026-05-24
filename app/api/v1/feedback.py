"""
User feedback and suggestions (authenticated users)
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.user_feedback import UserFeedback
from app.schemas.feedback import FeedbackCreate, FeedbackOut

router = APIRouter()


@router.post("/", response_model=FeedbackOut)
async def submit_feedback(
    payload: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit feedback or a product suggestion."""
    row = UserFeedback(
        id=uuid.uuid4(),
        user_id=current_user.id,
        title=payload.title,
        body=payload.body,
        category=payload.category,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
