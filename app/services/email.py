import structlog
import resend

from app.config.settings import settings

logger = structlog.get_logger()

resend.api_key = settings.RESEND_API_KEY


class EmailService:
    def __init__(self) -> None:
        self.from_address = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"

    def send(self, to: str, subject: str, html: str) -> bool:
        if not settings.RESEND_API_KEY:
            logger.warning("email_skipped", reason="RESEND_API_KEY not configured", to=to)
            return False
        try:
            resend.Emails.send(
                {"from": self.from_address, "to": to, "subject": subject, "html": html}
            )
            logger.info("email_sent", to=to, subject=subject)
            return True
        except Exception as e:
            logger.error("email_failed", to=to, error=str(e))
            return False

    def send_otp(self, to: str, code: str, purpose: str, expires_minutes: int) -> bool:
        subject_map = {
            "email_verification": "Verify your email",
            "password_reset": "Reset your password",
            "two_factor": "Your login code",
            "magic_link": "Your magic link code",
        }
        subject = subject_map.get(purpose, "Your verification code")
        html = f"""
        <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">
            <h2>{subject}</h2>
            <p>Your code is:</p>
            <div style="font-size: 36px; font-weight: bold; letter-spacing: 8px; padding: 20px;
                        background: #f4f4f4; text-align: center; border-radius: 8px;">
                {code}
            </div>
            <p style="color: #666;">This code expires in {expires_minutes} minutes.</p>
            <p style="color: #999; font-size: 12px;">If you didn't request this, ignore this email.</p>
        </div>
        """
        return self.send(to=to, subject=subject, html=html)

    def send_welcome(self, to: str, name: str) -> bool:
        return self.send(
            to=to,
            subject=f"Welcome to {settings.APP_NAME}!",
            html=f"<h2>Welcome, {name}!</h2><p>Thanks for joining {settings.APP_NAME}.</p>",
        )
