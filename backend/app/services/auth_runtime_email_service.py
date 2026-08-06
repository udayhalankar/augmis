import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.services.auth_runtime_state_service import (
    load_auth_runtime_state,
    save_auth_runtime_state,
    utcnow_iso,
)


def send_auth_email(
    *,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
    metadata: dict | None = None,
) -> dict:
    provider = (settings.AUTH_EMAIL_PROVIDER or "demo").strip().lower()

    if provider == "smtp" and settings.AUTH_SMTP_HOST and settings.AUTH_SMTP_USERNAME and settings.AUTH_SMTP_PASSWORD:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings.AUTH_SMTP_FROM_EMAIL
        message["To"] = to_email
        message.set_content(text_body)
        if html_body:
            message.add_alternative(html_body, subtype="html")

        with smtplib.SMTP(settings.AUTH_SMTP_HOST, settings.AUTH_SMTP_PORT) as server:
            server.starttls()
            server.login(settings.AUTH_SMTP_USERNAME, settings.AUTH_SMTP_PASSWORD)
            server.send_message(message)

        return {
            "provider": "smtp",
            "delivered": True,
            "preview": None,
        }

    state = load_auth_runtime_state()
    state.setdefault("email_log", []).append(
        {
            "to_email": to_email,
            "subject": subject,
            "text_body": text_body,
            "html_body": html_body,
            "metadata": metadata or {},
            "created_at": utcnow_iso(),
            "provider": provider,
        }
    )
    state["email_log"] = state["email_log"][-100:]
    save_auth_runtime_state(state)

    return {
        "provider": provider or "demo",
        "delivered": False,
        "preview": {
            "to_email": to_email,
            "subject": subject,
            "text_body": text_body,
            "html_body": html_body,
        },
    }
