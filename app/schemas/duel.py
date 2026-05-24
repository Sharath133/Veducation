"""
Duel Schemas
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from decimal import Decimal


class DuelRegistrationRequest(BaseModel):
    """Duel registration request"""
    duel_id: str
    name: str = Field(..., min_length=2, max_length=100)
    upi_mobile: str = Field(..., min_length=10, max_length=10, pattern=r'^[0-9]+$')


class PaymentOrderRequest(BaseModel):
    """Payment order request"""
    duel_id: str
    amount: Decimal
    name: str
    upi_mobile: str
    use_free_entry: bool = Field(
        default=False,
        description="If true, consume one free duel entry credit instead of creating a Razorpay order.",
    )


class PaymentVerifyRequest(BaseModel):
    """Payment verification request"""
    order_id: str
    payment_id: str
    signature: str
    duel_id: str
    name: str
    upi_mobile: str


class StartTestRequest(BaseModel):
    """Start test request"""
    duel_id: str
    language: str = Field(..., pattern="^(en|te)$")


class SubmitAnswerRequest(BaseModel):
    """Submit answer request (omit or null selected_answer to clear / save blank)."""

    registration_id: str
    question_id: str
    selected_answer: Optional[str] = None

    @field_validator("selected_answer", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        if v == "":
            return None
        return v

    @field_validator("selected_answer")
    @classmethod
    def validate_option(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if len(v) != 1 or v not in "ABCD":
            raise ValueError("selected_answer must be one of A, B, C, D when provided")
        return v


class SubmitTestRequest(BaseModel):
    """Submit test request"""
    attempt_id: str = Field(..., min_length=1, description="UUID of the test attempt")
    
    class Config:
        """Pydantic config"""
        json_schema_extra = {
            "example": {
                "attempt_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }


class TimerStartRequest(BaseModel):
    """Begin the server-side attempt clock (call after questions are loaded)."""

    attempt_id: str = Field(..., min_length=1, description="UUID of the test attempt")
