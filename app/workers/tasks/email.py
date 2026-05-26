import structlog

from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="email.send_otp", bind=True, max_retries=3, default_retry_delay=30)
def send_otp_email(
    self,
    to_email: str,
    code: str,
    purpose: str,
    expires_minutes: int,
) -> dict:
    try:
        from app.services.email import EmailService

        service = EmailService()
        success = service.send_otp(
            to=to_email, code=code, purpose=purpose, expires_minutes=expires_minutes
        )
        return {"success": success, "to": to_email}
    except Exception as exc:
        logger.error("send_otp_email_failed", error=str(exc), to=to_email)
        raise self.retry(exc=exc)


@celery_app.task(name="email.send_welcome", bind=True, max_retries=3, default_retry_delay=30)
def send_welcome_email(self, to_email: str, name: str) -> dict:
    try:
        from app.services.email import EmailService

        service = EmailService()
        success = service.send_welcome(to=to_email, name=name)
        return {"success": success, "to": to_email}
    except Exception as exc:
        logger.error("send_welcome_email_failed", error=str(exc), to=to_email)
        raise self.retry(exc=exc)
