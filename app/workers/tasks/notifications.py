import structlog

from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="notifications.send", bind=True, max_retries=3)
def send_notification(self, user_id: str, title: str, body: str, data: dict | None = None) -> dict:
    try:
        logger.info("notification_sent", user_id=user_id, title=title)
        return {"user_id": user_id, "title": title}
    except Exception as exc:
        raise self.retry(exc=exc)
