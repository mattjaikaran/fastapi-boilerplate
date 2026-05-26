from celery import Celery

from app.config.settings import settings

celery_app = Celery(
    "app",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.tasks.email",
        "app.workers.tasks.notifications",
        "app.workers.tasks.ml",
        "app.workers.tasks.maintenance",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_routes={
        "app.workers.tasks.email.*": {"queue": "email"},
        "app.workers.tasks.notifications.*": {"queue": "notifications"},
        "app.workers.tasks.ml.*": {"queue": "ml"},
    },
    task_default_queue="default",
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    beat_schedule={
        "expire-pending-api-keys": {
            "task": "app.workers.tasks.maintenance.expire_api_keys",
            "schedule": 3600.0,  # hourly
        },
        "cleanup-old-audit-logs": {
            "task": "app.workers.tasks.maintenance.cleanup_audit_logs",
            "schedule": 86400.0,  # daily
        },
        "cleanup-read-notifications": {
            "task": "app.workers.tasks.maintenance.cleanup_notifications",
            "schedule": 86400.0,  # daily
        },
    },
)
