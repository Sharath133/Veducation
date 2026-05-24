"""
Configuration Management
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "V Education API"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/veducation"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # OTP
    OTP_EXPIRE_MINUTES: int = 5
    OTP_LENGTH: int = 6
    OTP_RATE_LIMIT_MINUTES: int = 1
    
    # SMS Service (Twilio/MSG91)
    SMS_PROVIDER: str = "msg91"  # or "twilio"
    MSG91_API_KEY: str = ""
    MSG91_SENDER_ID: str = "VEDUCA"
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    
    # Razorpay
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Daily duel settlement (Celery beat uses Asia/Kolkata = IST)
    SETTLEMENT_TIMEZONE: str = "Asia/Kolkata"
    SETTLEMENT_DRY_RUN: bool = False
    # queue: persist payout rows for manual RazorpayX approval / later processing
    # auto: call Razorpay payouts API when credentials and fund_account_id are present
    SETTLEMENT_PAYOUT_MODE: str = "queue"
    SETTLEMENT_TOP_N: int = 10
    # RazorpayX / route account (header X-Razorpay-Account); never commit real secrets
    RAZORPAYX_ACCOUNT_ID: str = ""
    
    # AWS (for production)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-south-1"
    AWS_S3_BUCKET: str = ""

    # Local file uploads (admin PYQ PDF, etc.)
    UPLOAD_DIR: str = "uploads"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()

