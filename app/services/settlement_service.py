"""
Daily duel settlement: finalize ranks, top N rewards, persistence, Razorpay / queue payouts.

Timezone: ``settings.SETTLEMENT_TIMEZONE`` defaults to ``Asia/Kolkata`` (IST).
Idempotent per duel via ``duel_settlements`` row and phased status.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, List, Sequence
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import asc, desc, nullslast
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.integrations.razorpay_payout_client import RazorpayPayoutClient, RazorpayPayoutError
from app.services.settlement_prize_math import split_prize_pool_rupees
from app.models.duel import DailyDuel, Registration
from app.models.leaderboard import UserAttempt
from app.models.payment import Reward
from app.models.settlement import DuelSettlement, SettlementPayout
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SettlementSummary:
    duels_scanned: int
    duels_settled: int
    duels_skipped: int
    errors: List[str]


class DuelSettlementService:
    """
    Orchestrates settlement for eligible daily duels (``active`` / ``completed``).
    """

    @staticmethod
    def run_daily_settlement(session: Session) -> SettlementSummary:
        ist = ZoneInfo(settings.SETTLEMENT_TIMEZONE)
        today_ist = datetime.now(ist).date()
        today_str = today_ist.isoformat()
        errors: list[str] = []
        scanned = settled = skipped = 0

        duels = DuelSettlementService._load_eligible_duels(session, today_str)
        for duel in duels:
            scanned += 1
            try:
                outcome = DuelSettlementService._settle_one_duel(session, duel)
                session.commit()
                if outcome == "skipped":
                    skipped += 1
                elif outcome == "settled":
                    settled += 1
            except Exception as exc:  # noqa: BLE001 — boundary for job resilience
                session.rollback()
                msg = f"duel {duel.id} ({duel.duel_date}): {exc}"
                logger.exception("Settlement failed for %s", msg)
                errors.append(msg)

        return SettlementSummary(
            duels_scanned=scanned,
            duels_settled=settled,
            duels_skipped=skipped,
            errors=errors,
        )

    @staticmethod
    def _load_eligible_duels(session: Session, today_ist_iso: str) -> Sequence[DailyDuel]:
        return (
            session.query(DailyDuel)
            .filter(DailyDuel.status.in_(("active", "completed")))
            .filter(DailyDuel.duel_date < today_ist_iso)
            .order_by(DailyDuel.duel_date.asc())
            .all()
        )

    @staticmethod
    def _settle_one_duel(session: Session, duel: DailyDuel) -> str:
        settlement = DuelSettlementService._get_or_create_settlement(session, duel)
        if settlement.status == "completed":
            if duel.status != "settled":
                duel.status = "settled"
                return "settled"
            return "skipped"

        if settlement.status == "pending":
            DuelSettlementService._finalize_rankings(session, duel)
            settlement.status = "rankings_done"
            settlement.rankings_finalized_at = datetime.now(timezone.utc)

        if settlement.status == "rankings_done":
            DuelSettlementService._ensure_reward_and_payout_rows(session, duel, settlement)

        if settlement.status == "payouts_pending":
            DuelSettlementService._execute_payout_phase(session, duel, settlement)

        if settlement.status == "completed":
            duel.status = "settled"
            return "settled"
        return "skipped"

    @staticmethod
    def _get_or_create_settlement(session: Session, duel: DailyDuel) -> DuelSettlement:
        row = (
            session.query(DuelSettlement)
            .filter(DuelSettlement.duel_id == duel.id)
            .with_for_update(of=DuelSettlement)
            .one_or_none()
        )
        if row:
            return row
        row = DuelSettlement(duel_id=duel.id, status="pending")
        session.add(row)
        session.flush()
        return row

    @staticmethod
    def _finalize_rankings(session: Session, duel: DailyDuel) -> None:
        attempts = (
            session.query(UserAttempt)
            .join(Registration, Registration.id == UserAttempt.registration_id)
            .options(joinload(UserAttempt.user))
            .filter(UserAttempt.duel_id == duel.id)
            .filter(UserAttempt.submitted_at.isnot(None))
            .filter(Registration.payment_status == "completed")
            .all()
        )
        ordered = sorted(
            attempts,
            key=lambda a: (
                -DuelSettlementService._to_decimal(a.total_marks),
                a.time_taken_microseconds if a.time_taken_microseconds is not None else 10**18,
                str(a.user_id),
            ),
        )
        rank_by_attempt_id = {a.id: idx for idx, a in enumerate(ordered, start=1)}
        all_attempts = session.query(UserAttempt).filter(UserAttempt.duel_id == duel.id).all()
        for att in all_attempts:
            rnk = rank_by_attempt_id.get(att.id)
            if rnk is not None:
                att.rank = rnk
            else:
                att.rank = None
                att.reward_amount = Decimal("0")
                att.reward_status = "pending"
        session.flush()

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        if value is None:
            return Decimal("0")
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    @staticmethod
    def _ensure_reward_and_payout_rows(session: Session, duel: DailyDuel, settlement: DuelSettlement) -> None:
        existing = (
            session.query(SettlementPayout)
            .filter(SettlementPayout.settlement_id == settlement.id)
            .count()
        )
        if existing > 0:
            settlement.status = "payouts_pending"
            return

        top_n = max(1, int(settings.SETTLEMENT_TOP_N))
        winners = (
            session.query(UserAttempt)
            .join(Registration, Registration.id == UserAttempt.registration_id)
            .options(joinload(UserAttempt.user))
            .filter(UserAttempt.duel_id == duel.id)
            .filter(UserAttempt.submitted_at.isnot(None))
            .filter(Registration.payment_status == "completed")
            .order_by(
                desc(UserAttempt.total_marks),
                nullslast(asc(UserAttempt.time_taken_microseconds)),
                asc(UserAttempt.user_id),
            )
            .limit(top_n)
            .all()
        )
        pool = DuelSettlementService._to_decimal(duel.prize_pool)
        amounts = split_prize_pool_rupees(pool, len(winners))
        for attempt, amount in zip(winners, amounts):
            attempt.reward_amount = amount
            attempt.reward_status = "pending"
            ref = DuelSettlementService._payout_reference_id(duel.id, attempt.user_id)
            user = attempt.user
            fund_id = user.razorpay_fund_account_id if user else None
            payout = SettlementPayout(
                settlement_id=settlement.id,
                user_id=attempt.user_id,
                attempt_id=attempt.id,
                rank=attempt.rank or 0,
                amount_rupees=amount,
                reference_id=ref,
                razorpay_fund_account_id=fund_id,
                payout_status="pending",
            )
            session.add(payout)
            reward = Reward(
                user_id=attempt.user_id,
                attempt_id=attempt.id,
                duel_id=duel.id,
                rank=attempt.rank or 0,
                reward_amount=amount,
                payment_status="pending",
            )
            session.add(reward)
        session.flush()
        settlement.status = "payouts_pending"
        settlement.records_written_at = datetime.now(timezone.utc)

    @staticmethod
    def _payout_reference_id(duel_id: UUID, user_id: UUID) -> str:
        # Razorpay reference_id max length 40 — stable hash for idempotency across retries
        digest = hashlib.sha256(f"{duel_id}:{user_id}".encode("utf-8")).hexdigest()[:32]
        return f"vdd_{digest}"

    @staticmethod
    def _execute_payout_phase(session: Session, duel: DailyDuel, settlement: DuelSettlement) -> None:
        payouts: list[SettlementPayout] = (
            session.query(SettlementPayout)
            .filter(SettlementPayout.settlement_id == settlement.id)
            .with_for_update()
            .all()
        )
        dry = bool(settings.SETTLEMENT_DRY_RUN)
        mode = (settings.SETTLEMENT_PAYOUT_MODE or "queue").lower().strip()

        client: RazorpayPayoutClient | None = None
        if not dry and mode == "auto":
            client = RazorpayPayoutClient(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET,
                settings.RAZORPAYX_ACCOUNT_ID,
            )

        any_failed = False
        for po in payouts:
            if po.payout_status in ("processed", "dry_run", "queued", "skipped_no_account"):
                continue
            if dry:
                po.payout_status = "dry_run"
                po.last_error = None
                DuelSettlementService._sync_reward_attempt_after_payout(session, settlement, po, dry_run=True)
                continue

            if mode == "queue":
                po.payout_status = "queued"
                po.last_error = None
                DuelSettlementService._sync_reward_attempt_after_payout(session, settlement, po, queued=True)
                continue

            if mode != "auto":
                po.payout_status = "queued"
                DuelSettlementService._sync_reward_attempt_after_payout(session, settlement, po, queued=True)
                continue

            if not po.razorpay_fund_account_id:
                po.payout_status = "skipped_no_account"
                po.last_error = "User has no razorpay_fund_account_id"
                DuelSettlementService._sync_reward_attempt_after_payout(session, settlement, po, skipped=True)
                continue

            amount_paise = int((DuelSettlementService._to_decimal(po.amount_rupees) * Decimal("100")).to_integral_value(rounding=ROUND_HALF_UP))
            if amount_paise <= 0:
                po.payout_status = "skipped_no_account"
                po.last_error = "Non-positive payout amount"
                DuelSettlementService._sync_reward_attempt_after_payout(session, settlement, po, skipped=True)
                continue
            assert client is not None
            try:
                resp = client.create_payout(
                    fund_account_id=po.razorpay_fund_account_id,
                    amount_paise=amount_paise,
                    reference_id=po.reference_id,
                    narration=f"Duel {duel.duel_date}"[:30],
                )
                po.razorpay_payout_id = str(resp.get("id", "")) or None
                po.payout_status = "processed"
                po.last_error = None
                DuelSettlementService._sync_reward_attempt_after_payout(session, settlement, po, paid=True)
            except RazorpayPayoutError as exc:
                po.payout_status = "failed"
                po.last_error = str(exc)[:2000]
                any_failed = True
                logger.warning("Payout failed for %s: %s", po.reference_id, exc)

        if mode == "auto" and any_failed:
            settlement.status = "payouts_pending"
        else:
            settlement.status = "completed"
            settlement.completed_at = datetime.now(timezone.utc)
            duel.status = "settled"
        session.flush()

    @staticmethod
    def _sync_reward_attempt_after_payout(
        session: Session,
        settlement: DuelSettlement,
        payout: SettlementPayout,
        *,
        dry_run: bool = False,
        queued: bool = False,
        skipped: bool = False,
        paid: bool = False,
    ) -> None:
        reward = (
            session.query(Reward)
            .filter(Reward.attempt_id == payout.attempt_id)
            .filter(Reward.duel_id == settlement.duel_id)
            .one_or_none()
        )
        attempt = session.get(UserAttempt, payout.attempt_id)
        if dry_run:
            if reward:
                reward.payment_status = "pending"
                reward.payment_transaction_id = None
            if attempt:
                attempt.reward_status = "pending"
            return
        if skipped:
            if reward:
                reward.payment_status = "pending"
            if attempt:
                attempt.reward_status = "pending"
            return
        if queued:
            if reward:
                reward.payment_status = "processed"
                reward.payment_transaction_id = None
            if attempt:
                attempt.reward_status = "processed"
            return
        if paid:
            if reward:
                reward.payment_status = "paid"
                reward.payment_transaction_id = payout.razorpay_payout_id
                reward.processed_at = datetime.now(timezone.utc)
            if attempt:
                attempt.reward_status = "paid"
            return

