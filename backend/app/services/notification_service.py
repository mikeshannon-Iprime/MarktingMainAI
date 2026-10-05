"""Notification dispatcher — email, SMS, and delivery audit log."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.db.database import session_scope
from app.db.models import NotificationDelivery, User, UserSettings
from app.services.campaign_email import CampaignEmailError
from app.services import sms_client
from app.services.notification_email import notification_email_configured, send_notification_email
from app.services.sms_client import SmsDeliveryError, normalize_phone, send_sms, sms_configured

logger = logging.getLogger(__name__)

_IN_MEMORY_DELIVERIES: List[Dict[str, Any]] = []
_DELIVERY_COUNTER = 0

EVENT_LABELS = {
    "test_email": "Notification test email",
    "test_sms": "Notification test SMS",
    "job_auto_apply": "Job auto-apply summary",
    "campaign_sent": "Campaign delivery summary",
    "campaign_scheduled": "Campaign scheduled",
    "daily_report": "Daily performance report",
    "weekly_digest": "Weekly activity digest",
}


def _pg_backend() -> bool:
    from app.db.database import get_engine

    settings = get_settings()
    return get_engine() is not None and not settings.use_seed_data


def _resolve_user(session, user_external_id: str) -> Optional[User]:
    return session.query(User).filter(User.external_id == user_external_id).first()


def _load_preferences(user_external_id: str) -> Dict[str, Any]:
    from app.services.seed_data import get_user_profile, get_user_settings

    settings = get_user_settings(user_external_id)
    profile = get_user_profile(user_external_id)
    notifications = settings.get("notifications") or {}
    sms_phone = notifications.get("smsPhone") or profile.get("phone") or ""
    return {
        "email": profile.get("email") or "",
        "phone": profile.get("phone") or "",
        "smsPhone": sms_phone,
        "emailNotifications": bool(notifications.get("emailNotifications", True)),
        "smsNotifications": bool(notifications.get("smsNotifications", False)),
        "campaignAlerts": bool(notifications.get("campaignAlerts", True)),
        "jobAlerts": bool(notifications.get("jobAlerts", True)),
        "dailyReport": bool(notifications.get("dailyReport", False)),
        "weeklyDigest": bool(notifications.get("weeklyDigest", True)),
    }


def _record_delivery(
    *,
    user_external_id: Optional[str],
    channel: str,
    event_type: str,
    recipient: str,
    subject: Optional[str],
    body: Optional[str],
    status: str,
    provider_message_id: Optional[str] = None,
    error_message: Optional[str] = None,
) -> Dict[str, Any]:
    global _DELIVERY_COUNTER
    entry = {
        "id": f"nd-{_DELIVERY_COUNTER + 1}",
        "channel": channel,
        "eventType": event_type,
        "recipient": recipient,
        "subject": subject,
        "status": status,
        "providerMessageId": provider_message_id,
        "errorMessage": error_message,
        "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    _DELIVERY_COUNTER += 1

    if not _pg_backend():
        _IN_MEMORY_DELIVERIES.insert(0, entry)
        _IN_MEMORY_DELIVERIES[:] = _IN_MEMORY_DELIVERIES[:200]
        return entry

    with session_scope() as session:
        user_id = None
        if user_external_id:
            user = _resolve_user(session, user_external_id)
            user_id = user.id if user else None
        row = NotificationDelivery(
            user_id=user_id,
            channel=channel,
            event_type=event_type,
            recipient=recipient,
            subject=subject,
            body=body,
            status=status,
            provider_message_id=provider_message_id,
            error_message=error_message,
        )
        session.add(row)
        session.flush()
        entry["id"] = str(row.id)
    return entry


def get_notification_setup(user_external_id: Optional[str] = None) -> Dict[str, Any]:
    from app.services.campaign_email import merge_settings

    settings = get_settings()
    campaign_settings = merge_settings()
    if _pg_backend() and user_external_id:
        from app.services.pg_store import _load_campaign_settings_for_user

        campaign_settings = merge_settings(_load_campaign_settings_for_user(user_external_id))
    email_ready = notification_email_configured(campaign_settings)
    sms_ready = sms_configured()
    return {
        "emailConfigured": email_ready,
        "smsConfigured": sms_ready,
        "emailProvider": "smtp",
        "smsProvider": settings.sms_provider,
        "demoMode": bool(
            settings.notification_force_demo_mode
            or settings.campaign_force_demo_mode
            or (not email_ready and not sms_ready)
        ),
        "notificationFromName": settings.notification_from_name,
        "notificationFromEmail": settings.notification_from_email or campaign_settings.get("fromEmail") or "",
        "twilioFromNumber": settings.twilio_from_number or "",
    }


def get_notification_history(user_external_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    limit = max(1, min(limit, 100))
    if not _pg_backend():
        return _IN_MEMORY_DELIVERIES[:limit]

    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        if not user:
            return []
        rows = (
            session.query(NotificationDelivery)
            .filter(NotificationDelivery.user_id == user.id)
            .order_by(NotificationDelivery.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": str(row.id),
                "channel": row.channel,
                "eventType": row.event_type,
                "recipient": row.recipient,
                "subject": row.subject,
                "status": row.status,
                "providerMessageId": row.provider_message_id,
                "errorMessage": row.error_message,
                "createdAt": row.created_at.isoformat().replace("+00:00", "Z") if row.created_at else None,
            }
            for row in rows
        ]


def send_test_email(user_external_id: str, email: Optional[str] = None) -> Dict[str, Any]:
    prefs = _load_preferences(user_external_id)
    recipient = (email or prefs["email"]).strip()
    if not recipient:
        raise ValueError("Email address is required.")

    subject = "MarketingMind AI — notification test"
    body = (
        "This is a test notification from MarketingMind AI.\n"
        "If you received this message, your email notification channel is working."
    )
    from app.services.campaign_email import merge_settings

    settings = merge_settings()
    if _pg_backend() and user_external_id:
        from app.services.pg_store import _load_campaign_settings_for_user

        settings = merge_settings(_load_campaign_settings_for_user(user_external_id))
    try:
        result = send_notification_email(
            to_email=recipient,
            subject=subject,
            body_text=body,
            settings=settings,
        )
        _record_delivery(
            user_external_id=user_external_id,
            channel="email",
            event_type="test_email",
            recipient=recipient,
            subject=subject,
            body=body,
            status="sent",
            provider_message_id=result.get("messageId"),
        )
        return {
            "success": True,
            "mode": result.get("mode", "demo"),
            "message": f"Test email sent to {recipient}.",
        }
    except CampaignEmailError as exc:
        _record_delivery(
            user_external_id=user_external_id,
            channel="email",
            event_type="test_email",
            recipient=recipient,
            subject=subject,
            body=body,
            status="failed",
            error_message=str(exc),
        )
        raise


def send_test_sms(user_external_id: str, phone: Optional[str] = None) -> Dict[str, Any]:
    prefs = _load_preferences(user_external_id)
    recipient = normalize_phone(phone or prefs.get("smsPhone") or prefs.get("phone") or "")
    if not recipient:
        raise ValueError("SMS phone number is required.")

    body = "MarketingMind AI: Your SMS notifications are configured correctly."
    try:
        result = send_sms(to_phone=recipient, body=body)
        _record_delivery(
            user_external_id=user_external_id,
            channel="sms",
            event_type="test_sms",
            recipient=recipient,
            subject=None,
            body=body,
            status="sent",
            provider_message_id=result.get("messageId"),
        )
        return {
            "success": True,
            "mode": result.get("mode", "demo"),
            "message": result.get("message", f"Test SMS sent to {recipient}."),
        }
    except SmsDeliveryError as exc:
        _record_delivery(
            user_external_id=user_external_id,
            channel="sms",
            event_type="test_sms",
            recipient=recipient,
            subject=None,
            body=body,
            status="failed",
            error_message=str(exc),
        )
        raise


def notify_user(
    user_external_id: str,
    *,
    event_type: str,
    subject: str,
    body: str,
    preference_key: Optional[str] = None,
    send_email: bool = True,
    send_sms: bool = False,
) -> Dict[str, Any]:
    prefs = _load_preferences(user_external_id)
    if preference_key and not prefs.get(preference_key, True):
        return {"success": True, "skipped": True, "message": "Notification disabled by user preference."}

    deliveries: List[Dict[str, Any]] = []
    from app.services.campaign_email import merge_settings

    campaign_settings = merge_settings()
    if _pg_backend():
        from app.services.pg_store import _load_campaign_settings_for_user

        campaign_settings = merge_settings(_load_campaign_settings_for_user(user_external_id))

    if send_email and prefs["emailNotifications"] and prefs["email"]:
        try:
            result = send_notification_email(
                to_email=prefs["email"],
                subject=subject,
                body_text=body,
                settings=campaign_settings,
            )
            deliveries.append(
                _record_delivery(
                    user_external_id=user_external_id,
                    channel="email",
                    event_type=event_type,
                    recipient=prefs["email"],
                    subject=subject,
                    body=body,
                    status="sent",
                    provider_message_id=result.get("messageId"),
                )
            )
        except CampaignEmailError as exc:
            deliveries.append(
                _record_delivery(
                    user_external_id=user_external_id,
                    channel="email",
                    event_type=event_type,
                    recipient=prefs["email"],
                    subject=subject,
                    body=body,
                    status="failed",
                    error_message=str(exc),
                )
            )

    sms_target = normalize_phone(prefs.get("smsPhone") or prefs.get("phone") or "")
    if send_sms and prefs["smsNotifications"] and sms_target:
        sms_body = f"{subject}: {body}"[:320]
        try:
            # `send_sms` is shadowed by the bool keyword argument in this function.
            result = sms_client.send_sms(to_phone=sms_target, body=sms_body)
            deliveries.append(
                _record_delivery(
                    user_external_id=user_external_id,
                    channel="sms",
                    event_type=event_type,
                    recipient=sms_target,
                    subject=subject,
                    body=sms_body,
                    status="sent",
                    provider_message_id=result.get("messageId"),
                )
            )
        except SmsDeliveryError as exc:
            deliveries.append(
                _record_delivery(
                    user_external_id=user_external_id,
                    channel="sms",
                    event_type=event_type,
                    recipient=sms_target,
                    subject=subject,
                    body=sms_body,
                    status="failed",
                    error_message=str(exc),
                )
            )

    return {
        "success": True,
        "deliveries": deliveries,
        "message": f"Notification processed for {EVENT_LABELS.get(event_type, event_type)}.",
    }


def notify_job_auto_apply(user_external_id: str, summary: str, applied_count: int) -> None:
    try:
        notify_user(
            user_external_id,
            event_type="job_auto_apply",
            subject="Job auto-apply completed",
            body=f"{summary}\nApplied to {applied_count} job(s).",
            preference_key="jobAlerts",
            send_email=True,
            send_sms=True,
        )
    except Exception:
        logger.exception("Failed to send job auto-apply notification for %s", user_external_id)


def notify_campaign_launch(
    user_external_id: str,
    *,
    campaign_name: str,
    sent_count: int,
    status: str,
) -> None:
    try:
        event_type = "campaign_sent" if status.lower() == "sent" else "campaign_scheduled"
        notify_user(
            user_external_id,
            event_type=event_type,
            subject=f"Campaign {status.lower()}: {campaign_name}",
            body=f"Campaign '{campaign_name}' is {status.lower()} with {sent_count} recipient(s).",
            preference_key="campaignAlerts",
            send_email=True,
            send_sms=False,
        )
    except Exception:
        logger.exception("Failed to send campaign notification for %s", user_external_id)
