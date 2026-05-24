"""
Custom Validators
"""
import re
from typing import Optional


def validate_mobile_number(mobile: str) -> bool:
    """Validate Indian mobile number"""
    pattern = r'^[6-9]\d{9}$'
    return bool(re.match(pattern, mobile))


def validate_referral_code(code: str) -> bool:
    """Validate referral code format"""
    pattern = r'^[A-Z0-9]{6,10}$'
    return bool(re.match(pattern, code))


def generate_referral_code(user_id: str) -> str:
    """Generate unique referral code from user ID"""
    # Simple implementation - can be enhanced
    import hashlib
    hash_obj = hashlib.md5(user_id.encode())
    code = hash_obj.hexdigest()[:8].upper()
    return code

