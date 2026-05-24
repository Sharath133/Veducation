"""
Authentication Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import OTPRequest, OTPVerify, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/send-otp", response_model=dict)
async def send_otp(request: OTPRequest, db: Session = Depends(get_db)):
    """Send OTP to mobile number"""
    service = AuthService(db)
    result = await service.send_otp(request.mobile_number, request.purpose)
    return result


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(request: OTPVerify, db: Session = Depends(get_db)):
    """Verify OTP and return JWT tokens"""
    service = AuthService(db)
    result = await service.verify_otp(request.mobile_number, request.otp_code)
    return result


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    """Refresh access token"""
    service = AuthService(db)
    result = await service.refresh_token(refresh_token)
    return result


@router.post("/logout")
async def logout():
    """Logout user"""
    return {"message": "Logged out successfully"}

