"""
Celery application (broker/result from settings; no secrets in code).
Beat: daily settlement shortly after midnight IST (``Asia/Kolkata``).
"""
from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery = Celery(
    "veducation",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.settlement_tasks"],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.SETTLEMENT_TIMEZONE,
    enable_utc=True,
)

celery.conf.beat_schedule = {
    "daily-duel-settlement-ist": {
        "task": "app.tasks.settlement_tasks.run_daily_settlement",
        # After 12:00 AM India Standard Time (IST = Asia/Kolkata)
        "schedule": crontab(hour=0, minute=5, timezone=settings.SETTLEMENT_TIMEZONE),
    },
}
