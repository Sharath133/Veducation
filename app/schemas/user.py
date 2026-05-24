"""
User Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserProfile(BaseModel):
    """User Profile schema"""
    id: UUID
    mobile_number: str
    name: Optional[str]
    upi_mobile: Optional[str]
    referral_code: str
    loyalty_points: int
    is_admin: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    """User Profile Update schema"""
    name: Optional[str] = None
    upi_mobile: Optional[str] = None


class MobileChangeSendRequest(BaseModel):
    """Request OTP for changing the authenticated user's mobile number."""
    new_mobile_number: str = Field(..., min_length=10, max_length=15)


class MobileChangeConfirmRequest(BaseModel):
    """Confirm mobile change with OTP sent to the new number."""
    new_mobile_number: str = Field(..., min_length=10, max_length=15)
    otp_code: str = Field(..., min_length=4, max_length=6)

