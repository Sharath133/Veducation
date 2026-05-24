"""
OTP Service - SMS Integration
"""
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class OTPService:
    """OTP Service for sending SMS"""
    
    async def send_otp(self, mobile_number: str, otp_code: str) -> bool:
        """Send OTP via SMS"""
        if settings.SMS_PROVIDER == "msg91":
            return await self._send_via_msg91(mobile_number, otp_code)
        elif settings.SMS_PROVIDER == "twilio":
            return await self._send_via_twilio(mobile_number, otp_code)
        else:
            # For development, just log
            logger.info(f"OTP for {mobile_number}: {otp_code}")
            return True
    
    async def _send_via_msg91(self, mobile_number: str, otp_code: str) -> bool:
        """Send OTP via MSG91"""
        # TODO: Implement MSG91 integration
        logger.info(f"MSG91 OTP to {mobile_number}: {otp_code}")
        return True
    
    async def _send_via_twilio(self, mobile_number: str, otp_code: str) -> bool:
        """Send OTP via Twilio"""
        # TODO: Implement Twilio integration
        logger.info(f"Twilio OTP to {mobile_number}: {otp_code}")
        return True

