"""
Payment Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from decimal import Decimal
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.duel import DailyDuel, Registration
from app.models.payment import Payment
from app.schemas.duel import PaymentOrderRequest, PaymentVerifyRequest
import uuid
import hashlib
import hmac
import base64

router = APIRouter()

# TODO: Move to environment variables
RAZORPAY_KEY_ID = "rzp_test_1234567890"  # Replace with actual key
RAZORPAY_KEY_SECRET = "test_secret_key"  # Replace with actual secret


@router.post("/create-order")
async def create_order(
    request: PaymentOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Razorpay order"""
    try:
        duel_uuid = uuid.UUID(str(request.duel_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid duel_id")

    # Verify duel exists
    duel = db.query(DailyDuel).filter(DailyDuel.id == duel_uuid).first()
    if not duel:
        raise HTTPException(status_code=404, detail="Duel not found")
    
    # Check if already registered
    existing_reg = db.query(Registration).filter(
        Registration.duel_id == duel_uuid,
        Registration.user_id == current_user.id
    ).first()
    
    if existing_reg and existing_reg.payment_status == "completed":
        raise HTTPException(status_code=400, detail="Already registered for this duel")

    if request.use_free_entry:
        credits = int(current_user.free_duel_entry_credits or 0)
        if credits < 1:
            raise HTTPException(
                status_code=400,
                detail="No free duel entry credits available. Redeem loyalty points or complete payment.",
            )

        current_user.name = request.name
        current_user.upi_mobile = request.upi_mobile

        registration_id = uuid.uuid4()
        if not existing_reg:
            registration = Registration(
                id=registration_id,
                user_id=current_user.id,
                duel_id=duel_uuid,
                payment_status="completed",
                payment_amount=Decimal("0.00"),
                payment_id=f"free_duel_entry_{uuid.uuid4().hex[:16]}",
            )
            db.add(registration)
        else:
            registration = existing_reg
            registration_id = existing_reg.id
            registration.payment_status = "completed"
            registration.payment_amount = Decimal("0.00")
            registration.payment_id = f"free_duel_entry_{uuid.uuid4().hex[:16]}"

        current_user.free_duel_entry_credits = credits - 1
        db.commit()
        db.refresh(registration)

        return {
            "order_id": None,
            "razorpay_key": None,
            "amount": 0.0,
            "currency": "INR",
            "registration_id": str(registration_id),
            "used_free_entry": True,
        }
    
    # Create registration (pending payment)
    registration_id = uuid.uuid4()
    if not existing_reg:
        registration = Registration(
            id=registration_id,
            user_id=current_user.id,
            duel_id=duel_uuid,
            payment_status="pending",
            payment_amount=request.amount
        )
        db.add(registration)
    else:
        registration = existing_reg
        registration_id = existing_reg.id
        registration.payment_amount = request.amount
    
    db.commit()
    
    # Generate Razorpay order ID (mock for now)
    order_id = f"order_{uuid.uuid4().hex[:16]}"
    
    return {
        "order_id": order_id,
        "razorpay_key": RAZORPAY_KEY_ID,
        "amount": float(request.amount),
        "currency": "INR",
        "registration_id": str(registration_id),
        "used_free_entry": False,
    }


@router.post("/verify")
async def verify_payment(
    request: PaymentVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify Razorpay payment"""
    # Verify payment signature (simplified - actual implementation would verify with Razorpay)
    # For now, we'll accept any payment for testing
    
    # Find registration
    registration = db.query(Registration).filter(
        Registration.duel_id == request.duel_id,
        Registration.user_id == current_user.id
    ).first()
    
    if not registration:
        raise HTTPException(status_code=404, detail="Registration not found")
    
    # Update user name and UPI mobile
    current_user.name = request.name
    current_user.upi_mobile = request.upi_mobile
    
    # Create payment record
    payment = Payment(
        id=uuid.uuid4(),
        registration_id=registration.id,
        razorpay_order_id=request.order_id,
        razorpay_payment_id=request.payment_id,
        razorpay_signature=request.signature,
        amount=registration.payment_amount or Decimal("5.00"),
        status="completed"
    )
    db.add(payment)
    
    # Update registration
    registration.payment_status = "completed"
    registration.payment_id = request.payment_id
    
    db.commit()
    
    return {
        "success": True,
        "message": "Payment verified and registration completed",
        "registration_id": str(registration.id)
    }


@router.get("/status/{payment_id}")
async def get_payment_status(payment_id: str, db: Session = Depends(get_db)):
    """Get payment status"""
    payment = db.query(Payment).filter(Payment.razorpay_payment_id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return {
        "payment_id": payment_id,
        "status": payment.status,
        "amount": float(payment.amount)
    }


@router.post("/bypass-for-testing")
async def bypass_payment_for_testing(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bypass payment for testing purposes - DO NOT USE IN PRODUCTION"""
    duel_id = request.get("duel_id")
    name = request.get("name", "Test User")
    upi_mobile = request.get("upi_mobile", current_user.mobile_number)
    
    if not duel_id:
        raise HTTPException(status_code=400, detail="duel_id is required")
    
    # Verify duel exists
    duel = db.query(DailyDuel).filter(DailyDuel.id == duel_id).first()
    if not duel:
        raise HTTPException(status_code=404, detail="Duel not found")
    
    # Check if already registered
    existing_reg = db.query(Registration).filter(
        Registration.duel_id == duel_id,
        Registration.user_id == current_user.id
    ).first()
    
    if existing_reg and existing_reg.payment_status == "completed":
        return {
            "success": True,
            "message": "Already registered",
            "registration_id": str(existing_reg.id)
        }
    
    # Update user name and UPI mobile
    current_user.name = name
    current_user.upi_mobile = upi_mobile
    
    # Create registration with completed payment status (bypass)
    registration_id = uuid.uuid4()
    if not existing_reg:
        registration = Registration(
            id=registration_id,
            user_id=current_user.id,
            duel_id=uuid.UUID(duel_id),
            payment_status="completed",  # Bypass payment
            payment_amount=duel.registration_fee,
            payment_id=f"test_bypass_{uuid.uuid4().hex[:16]}"
        )
        db.add(registration)
    else:
        registration = existing_reg
        registration_id = existing_reg.id
        registration.payment_status = "completed"
        registration.payment_amount = duel.registration_fee
        registration.payment_id = f"test_bypass_{uuid.uuid4().hex[:16]}"
    
    db.commit()
    
    return {
        "success": True,
        "message": "Registration completed (payment bypassed for testing)",
        "registration_id": str(registration_id)
    }

