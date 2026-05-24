"""
Referral API schemas
"""
from pydantic import BaseModel, Field


class ApplyReferralCodeRequest(BaseModel):
    """Body for applying a friend's referral code."""

    referral_code: str = Field(..., min_length=1, max_length=20, description="Referrer's code")
