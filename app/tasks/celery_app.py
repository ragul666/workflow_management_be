from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "compliance_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "check-sla-every-5-minutes": {
            "task": "app.tasks.sla_tasks.check_sla_breaches",
            "schedule": crontab(minute="*/5"),
        },
    },
)
