"""
Celery tasks for duel settlement.
"""
from app.celery_app import celery
from app.database import SessionLocal
from app.services.settlement_service import DuelSettlementService


@celery.task(name="app.tasks.settlement_tasks.run_daily_settlement")
def run_daily_settlement() -> dict:
    """
    Finalize rankings, persist rewards / payout rows, queue or execute Razorpay payouts.
    Safe to retry; per-duel idempotency is enforced in the service layer.
    """
    session = SessionLocal()
    try:
        summary = DuelSettlementService.run_daily_settlement(session)
        return {
            "duels_scanned": summary.duels_scanned,
            "duels_settled": summary.duels_settled,
            "duels_skipped": summary.duels_skipped,
            "errors": summary.errors,
        }
    finally:
        session.close()
