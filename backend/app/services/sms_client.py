"""SMS delivery — Twilio when configured, demo mode otherwise."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional
from urllib import error, parse, request

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SmsDeliveryError(Exception):
    """Raised when SMS delivery fails."""


def sms_configured() -> bool:
    settings = get_settings()
    if settings.notification_force_demo_mode or settings.sms_provider == "demo":
        return False
    return bool(
        settings.sms_provider == "twilio"
        and settings.twilio_account_sid
        and settings.twilio_auth_token
        and settings.twilio_from_number
    )


def normalize_phone(phone: str) -> str:
    digits = "".join(char for char in phone if char.isdigit() or char == "+")
    if not digits:
        return ""
    if digits.startswith("+"):
        return digits
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return f"+{digits}"


def send_sms(*, to_phone: str, body: str) -> Dict[str, Any]:
    settings = get_settings()
    destination = normalize_phone(to_phone)
    if not destination:
        raise SmsDeliveryError("A valid phone number is required for SMS delivery.")

    if sms_configured():
        return _send_twilio_sms(destination, body)

    message_id = f"demo-sms-{uuid.uuid4().hex[:12]}"
    logger.info("SMS demo mode: to=%s body=%s", destination, body[:120])
    return {
        "success": True,
        "mode": "demo",
        "messageId": message_id,
        "recipient": destination,
        "message": f"SMS simulated to {destination}.",
    }


def _send_twilio_sms(to_phone: str, body: str) -> Dict[str, Any]:
    settings = get_settings()
    account_sid = settings.twilio_account_sid or ""
    auth_token = settings.twilio_auth_token or ""
    from_number = settings.twilio_from_number or ""

    payload = parse.urlencode(
        {
            "To": to_phone,
            "From": from_number,
            "Body": body[:1600],
        }
    ).encode("utf-8")
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    http_request = request.Request(url, data=payload, method="POST")
    credentials = f"{account_sid}:{auth_token}".encode("utf-8")
    import base64

    http_request.add_header("Authorization", f"Basic {base64.b64encode(credentials).decode('ascii')}")
    http_request.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with request.urlopen(http_request, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SmsDeliveryError(f"Twilio SMS failed ({exc.code}): {detail}") from exc
    except error.URLError as exc:
        raise SmsDeliveryError(f"Twilio SMS network error: {exc.reason}") from exc

    message_id = "twilio-sent"
    if '"sid":' in raw:
        try:
            import json

            message_id = json.loads(raw).get("sid", message_id)
        except Exception:
            pass

    return {
        "success": True,
        "mode": "live",
        "messageId": message_id,
        "recipient": to_phone,
        "message": f"SMS sent to {to_phone}.",
    }


def test_sms_connection(to_phone: str, body: Optional[str] = None) -> Dict[str, Any]:
    message = body or "MarketingMind AI: Your SMS notifications are configured correctly."
    result = send_sms(to_phone=to_phone, body=message)
    return {
        "success": True,
        "mode": result.get("mode", "demo"),
        "message": result.get("message", "SMS test completed."),
    }
