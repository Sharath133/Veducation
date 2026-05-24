"""
Duel settlement and payout tracking (daily job).
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Numeric, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class DuelSettlement(Base):
    """
    One row per duel — idempotency anchor for the settlement job.
    IST calendar semantics are enforced in the service layer (Asia/Kolkata).
    """
    __tablename__ = "duel_settlements"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    duel_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("daily_duels.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    status = Column(
        String(32),
        nullable=False,
        default="pending",
        index=True,
    )
    # pending | rankings_done | records_written | payouts_pending | completed | failed
    error_message = Column(Text, nullable=True)
    rankings_finalized_at = Column(DateTime(timezone=True), nullable=True)
    records_written_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    duel = relationship("DailyDuel", backref="settlement", uselist=False)
    payouts = relationship("SettlementPayout", back_populates="settlement", cascade="all, delete-orphan")


class SettlementPayout(Base):
    """
    Per-winner payout line item; reference_id is stable for Razorpay idempotency / retries.
    """
    __tablename__ = "settlement_payouts"
    __table_args__ = (UniqueConstraint("reference_id", name="uq_settlement_payout_reference_id"),)

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    settlement_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("duel_settlements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    attempt_id = Column(Uuid(as_uuid=True), ForeignKey("user_attempts.id"), nullable=False, index=True)
    rank = Column(Integer, nullable=False)
    amount_rupees = Column(Numeric(12, 2), nullable=False)
    reference_id = Column(String(128), nullable=False)
    razorpay_fund_account_id = Column(String(255), nullable=True)
    razorpay_payout_id = Column(String(255), nullable=True)
    payout_status = Column(
        String(32),
        nullable=False,
        default="pending",
        index=True,
    )
    # pending | queued | submitted | processing | processed | failed | dry_run | skipped_no_account
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    settlement = relationship("DuelSettlement", back_populates="payouts")
