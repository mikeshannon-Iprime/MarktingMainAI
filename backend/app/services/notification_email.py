"""Transactional notification email — reuses campaign SMTP infrastructure."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.config import get_settings
from app.services.campaign_email import CampaignEmailError, merge_settings, send_single_email, smtp_configured


def notification_email_configured(settings: Optional[Dict[str, Any]] = None) -> bool:
    merged = merge_settings(settings)
    app = get_settings()
    if app.campaign_force_demo_mode:
        return False
    return smtp_configured(merged)


def build_notification_html(title: str, body: str) -> str:
    return (
        "<!DOCTYPE html><html><body style='font-family:Arial,sans-serif;line-height:1.5;color:#111827;'>"
        f"<h2 style='margin:0 0 12px;'>{title}</h2>"
        f"<p>{body}</p>"
        "<p style='font-size:12px;color:#6b7280;margin-top:24px;'>MarketingMind AI Notifications</p>"
        "</body></html>"
    )


def send_notification_email(
    *,
    to_email: str,
    subject: str,
    body_text: str,
    settings: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    app = get_settings()
    merged = merge_settings(settings)
    from_name = app.notification_from_name
    from_email = app.notification_from_email or merged.get("fromEmail") or merged.get("smtpUsername") or ""
    html = build_notification_html(subject, body_text.replace("\n", "<br/>"))
    try:
        return send_single_email(
            to_email=to_email,
            subject=subject,
            body_html=html,
            from_name=from_name,
            from_email=from_email,
            reply_to=from_email,
            settings=merged,
            contact={"email": to_email, "name": to_email.split("@")[0]},
        )
    except CampaignEmailError as exc:
        raise CampaignEmailError(str(exc)) from exc
