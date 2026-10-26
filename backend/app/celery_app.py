"""Celery app + beat schedule. Run with:
  celery -A app.celery_app worker --loglevel=info
  celery -A app.celery_app beat --loglevel=info
"""
from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "uzhavan",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    "scrape-agmarknet-daily": {
        "task": "app.tasks.scrape_agmarknet_prices",
        "schedule": crontab(hour=5, minute=30),  # after mandi opening reports settle
    },
    "scrape-retail-prices-daily": {
        "task": "app.tasks.scrape_retail_prices",
        "schedule": crontab(hour=6, minute=0),
    },
    "recompute-fair-prices-daily": {
        "task": "app.tasks.recompute_fair_prices",
        "schedule": crontab(hour=6, minute=30),
    },
    "run-logistics-pooling-hourly": {
        "task": "app.tasks.run_logistics_pooling",
        "schedule": crontab(minute=0),
    },
    "reset-daily-processing-intake-midnight": {
        "task": "app.tasks.reset_daily_processing_intake",
        "schedule": crontab(hour=0, minute=0),
    },
}
