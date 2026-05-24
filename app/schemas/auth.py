"""
Authentication Schemas
"""
from pydantic import BaseModel, Field


class OTPRequest(BaseModel):
    """OTP Request schema"""
    mobile_number: str = Field(..., min_length=10, max_length=15)
    purpose: str = Field(..., pattern="^(login|registration)$")


class OTPVerify(BaseModel):
    """OTP Verify schema"""
    mobile_number: str = Field(..., min_length=10, max_length=15)
    otp_code: str = Field(..., min_length=4, max_length=6)


class TokenResponse(BaseModel):
    """Token Response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

