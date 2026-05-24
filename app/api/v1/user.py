"""
User Endpoints
"""
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.admin_user_message import AdminUserMessage
from app.schemas.user import (
    UserProfile,
    UserProfileUpdate,
    MobileChangeSendRequest,
    MobileChangeConfirmRequest,
)
from app.services.auth_service import AuthService
from app.schemas.admin_user_message import AdminUserMessageOut

router = APIRouter()


@router.get("/profile", response_model=UserProfile)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get user profile"""
    return current_user


@router.put("/profile", response_model=UserProfile)
async def update_profile(
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update name and UPI mobile (login mobile is changed via OTP flow)."""
    if profile_update.name is not None:
        current_user.name = profile_update.name
    if profile_update.upi_mobile is not None:
        current_user.upi_mobile = profile_update.upi_mobile
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/profile/mobile-change/send-otp", response_model=dict)
async def send_mobile_change_otp(
    body: MobileChangeSendRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send OTP to the new mobile number before updating the account."""
    service = AuthService(db)
    try:
        return await service.send_mobile_change_otp(current_user, body.new_mobile_number)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/profile/mobile-change/confirm", response_model=UserProfile)
async def confirm_mobile_change(
    body: MobileChangeConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verify OTP and set the authenticated user's mobile to the new number."""
    service = AuthService(db)
    try:
        user = await service.verify_mobile_change(
            current_user, body.new_mobile_number, body.otp_code
        )
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/admin-messages", response_model=List[AdminUserMessageOut])
async def list_admin_messages(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
):
    """Messages sent to this user by admins (newest first)."""
    cap = min(max(limit, 1), 100)
    rows = (
        db.query(AdminUserMessage)
        .filter(AdminUserMessage.user_id == current_user.id)
        .order_by(desc(AdminUserMessage.created_at))
        .limit(cap)
        .all()
    )
    return [AdminUserMessageOut.model_validate(r) for r in rows]


@router.patch("/admin-messages/{message_id}/read", response_model=AdminUserMessageOut)
async def mark_admin_message_read(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        mid = uuid.UUID(message_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid message_id") from exc

    msg = (
        db.query(AdminUserMessage)
        .filter(AdminUserMessage.id == mid, AdminUserMessage.user_id == current_user.id)
        .first()
    )
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    if msg.read_at is None:
        msg.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(msg)
    return AdminUserMessageOut.model_validate(msg)
