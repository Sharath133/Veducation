"""
Helper Functions
"""
import random
import string
from datetime import datetime, timezone
from typing import Optional


def generate_otp(length: int = 6) -> str:
    """Generate random OTP"""
    return ''.join(random.choices(string.digits, k=length))


def get_current_timestamp() -> datetime:
    """Get current UTC timestamp"""
    return datetime.now(timezone.utc)


def calculate_time_microseconds(start_time: datetime, end_time: datetime) -> int:
    """Calculate time difference in microseconds"""
    delta = end_time - start_time
    return int(delta.total_seconds() * 1_000_000)


def format_microseconds(microseconds: int) -> str:
    """Format microseconds to readable time string"""
    total_seconds = microseconds / 1_000_000
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    micros = int((total_seconds % 1) * 1_000_000)
    return f"{minutes:02d}:{seconds:02d}.{micros:06d}"

