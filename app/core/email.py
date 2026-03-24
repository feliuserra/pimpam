"""
Transactional email delivery via SMTP (aiosmtplib).

All public functions are no-ops when smtp_enabled=False so the app works
without email configuration in development.
"""
from email.mime.text import MIMEText

from app.core.config import settings


async def send_email(to: str, subject: str, body: str) -> None:
    """Send a plain-text email. Silently skipped when SMTP is disabled."""
    if not settings.smtp_enabled:
        return
    import aiosmtplib

    msg = MIMEText(body)
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username or None,
        password=settings.smtp_password or None,
        start_tls=settings.smtp_tls,
    )


async def send_verification_email(to: str, token: str) -> None:
    """Send an email verification link to a newly registered user."""
    subject = "Verify your PimPam email address"
    body = (
        f"Welcome to PimPam! Click the link below to verify your email address "
        f"(valid for {settings.email_verification_token_expire_minutes} minutes):\n\n"
        f"https://{settings.domain}/verify-email?token={token}\n\n"
        "If you didn't create a PimPam account, you can safely ignore this email."
    )
    await send_email(to, subject, body)


async def send_password_reset_email(to: str, token: str, mode: str) -> None:
    """Send a password reset link or code to the user."""
    if mode == "code":
        subject = "Your PimPam password reset code"
        body = (
            f"Your password reset code is:\n\n"
            f"    {token}\n\n"
            f"This code is valid for {settings.password_reset_code_expire_minutes} minutes.\n\n"
            "If you didn't request a password reset, you can safely ignore this email."
        )
    else:
        subject = "Reset your PimPam password"
        body = (
            f"Click the link below to reset your password "
            f"(valid for {settings.password_reset_link_expire_minutes} minutes):\n\n"
            f"https://{settings.domain}/reset-password?token={token}\n\n"
            "If you didn't request a password reset, you can safely ignore this email."
        )
    await send_email(to, subject, body)
