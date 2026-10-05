from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.passwords import hash_password, verify_password
from app.db.database import get_engine, session_scope
from app.db.models import AuthSession, User, UserSettings

logger = get_logger(__name__)

ROLE_USER = "user"
ROLE_ADMIN = "admin"
ROLE_SUPER_ADMIN = "super_admin"
ALL_ROLES = [ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_USER]

DEMO_EMAILS = (
    "superadmin@marketingmind.ai",
    "admin@marketingmind.ai",
    "user@marketingmind.ai",
)


class AuthError(Exception):
    pass


def _clean_email(email: str) -> str:
    return email.strip().lower()


def _sanitize_user(user: User) -> dict:
    return {
        "id": user.external_id or str(user.id),
        "name": user.name,
        "email": user.email,
        "role": user.role,
    }


def _session_expiry() -> datetime:
    settings = get_settings()
    hours = getattr(settings, "jwt_expiration_hours", None) or 24
    return datetime.now(timezone.utc) + timedelta(hours=hours)


def _get_user_by_email(session: Session, email: str) -> User | None:
    return session.query(User).filter(User.email == _clean_email(email)).first()


def _get_user_by_external_id(session: Session, external_id: str) -> User | None:
    return session.query(User).filter(User.external_id == external_id).first()


def get_user_by_external_id(external_id: str) -> User | None:
    with session_scope() as session:
        return _get_user_by_external_id(session, external_id)


def get_auth_options() -> dict:
    with session_scope() as session:
        demo_users = (
            session.query(User)
            .filter(User.email.in_(DEMO_EMAILS))
            .order_by(User.id)
            .all()
        )
        return {
            "roles": ALL_ROLES,
            "demoUsers": [
                {
                    "name": user.name,
                    "email": user.email,
                    "role": user.role,
                }
                for user in demo_users
            ],
        }


def login_user(email: str, password: str) -> dict:
    clean_email = _clean_email(email)
    with session_scope() as session:
        user = _get_user_by_email(session, clean_email)
        if not user or not user.is_active:
            logger.warning("Login failed for %s: user not found or inactive", clean_email)
            raise AuthError("Invalid email or password.")
        if not verify_password(password, user.password_hash):
            logger.warning("Login failed for %s: invalid password", clean_email)
            raise AuthError("Invalid email or password.")

        token = str(uuid4())
        session.add(
            AuthSession(
                token=token,
                user_id=user.id,
                email=user.email,
                expires_at=_session_expiry(),
            )
        )
        user.last_login = datetime.now(timezone.utc)
        session.flush()
        logger.info("Login success for %s (role=%s)", clean_email, user.role)
        return {"token": token, "user": _sanitize_user(user)}


def register_user(name: str, email: str, password: str, role: str = ROLE_USER) -> dict:
    clean_email = _clean_email(email)
    requested_role = role.strip().lower()
    if requested_role not in ALL_ROLES:
        raise AuthError("Invalid role.")

    with session_scope() as session:
        if _get_user_by_email(session, clean_email):
            raise AuthError("User already exists for this email.")

        external_id = f"u-{uuid4().hex[:8]}"
        user = User(
            external_id=external_id,
            name=name.strip() or "New User",
            email=clean_email,
            password_hash=hash_password(password),
            role=requested_role,
            company="MarketingMind",
            title="Recruiter",
            department="Operations",
            location="",
            timezone="UTC",
            bio="",
        )
        session.add(user)
        session.flush()
        session.add(UserSettings(user_id=user.id))

        token = str(uuid4())
        session.add(
            AuthSession(
                token=token,
                user_id=user.id,
                email=user.email,
                expires_at=_session_expiry(),
            )
        )
        session.flush()
        logger.info("Registered user %s (role=%s)", clean_email, requested_role)
        return {"token": token, "user": _sanitize_user(user)}


def logout_user(token: str) -> None:
    with session_scope() as session:
        deleted = session.query(AuthSession).filter(AuthSession.token == token).delete()
        if deleted:
            logger.info("User session revoked")


def resolve_user_from_token(token: str) -> dict:
    with session_scope() as session:
        auth_session = session.query(AuthSession).filter(AuthSession.token == token).first()
        if not auth_session:
            raise AuthError("Invalid or expired session token.")

        now = datetime.now(timezone.utc)
        if auth_session.expires_at and auth_session.expires_at < now:
            session.delete(auth_session)
            raise AuthError("Invalid or expired session token.")

        # Sliding session: renew the expiry when less than half the lifetime
        # remains, so active users keep their session across days of use.
        full_expiry = _session_expiry()
        if auth_session.expires_at:
            remaining = auth_session.expires_at - now
            lifetime = full_expiry - now
            if remaining < lifetime / 2:
                auth_session.expires_at = full_expiry

        user = session.query(User).filter(User.id == auth_session.user_id).first()
        if not user or not user.is_active:
            raise AuthError("User session is no longer valid.")

        payload = _sanitize_user(user)
        payload["token"] = token
        return payload


def get_user_profile(user_external_id: str) -> dict:
    with session_scope() as session:
        user = _get_user_by_external_id(session, user_external_id)
        if not user:
            raise ValueError("User not found.")
        created = user.created_at.isoformat().replace("+00:00", "Z") if user.created_at else None
        last_login = user.last_login.isoformat().replace("+00:00", "Z") if user.last_login else created
        return {
            "id": user.external_id or str(user.id),
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "phone": user.phone or "",
            "company": user.company or "",
            "title": user.title or "",
            "department": user.department or "",
            "location": user.location or "",
            "timezone": user.timezone or "UTC",
            "bio": user.bio or "",
            "createdAt": created,
            "lastLogin": last_login,
        }


def update_user_profile(user_external_id: str, updates: dict) -> None:
    allowed_fields = {
        "name": "name",
        "phone": "phone",
        "company": "company",
        "title": "title",
        "department": "department",
        "location": "location",
        "timezone": "timezone",
        "bio": "bio",
    }
    with session_scope() as session:
        user = _get_user_by_external_id(session, user_external_id)
        if not user:
            raise ValueError("User not found.")
        for key, attr in allowed_fields.items():
            if key in updates and updates[key] is not None:
                setattr(user, attr, updates[key])


def change_user_password(user_external_id: str, current_password: str, new_password: str, confirm_password: str) -> None:
    if new_password != confirm_password:
        raise ValueError("New passwords do not match.")
    if len(new_password) < 6:
        raise ValueError("Password must be at least 6 characters.")

    with session_scope() as session:
        user = _get_user_by_external_id(session, user_external_id)
        if not user:
            raise ValueError("User not found.")
        if not verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect.")
        user.password_hash = hash_password(new_password)


def get_user_settings(user_external_id: str) -> dict:
    with session_scope() as session:
        user = _get_user_by_external_id(session, user_external_id)
        if not user:
            raise ValueError("User not found.")
        settings = user.settings
        if not settings:
            settings = UserSettings(user_id=user.id)
            session.add(settings)
            session.flush()
        return {
            "notifications": {
                "emailNotifications": settings.email_notifications,
                "campaignAlerts": settings.campaign_alerts,
                "jobAlerts": settings.job_alerts,
                "dailyReport": settings.daily_report,
                "weeklyDigest": settings.weekly_digest,
                "smsNotifications": settings.sms_notifications,
                "smsPhone": settings.sms_phone or user.phone or "",
            },
            "language": settings.language,
            "dateFormat": settings.date_format,
            "theme": settings.theme,
        }


def update_user_settings(user_external_id: str, settings_payload: dict) -> None:
    with session_scope() as session:
        user = _get_user_by_external_id(session, user_external_id)
        if not user:
            raise ValueError("User not found.")
        settings = user.settings
        if not settings:
            settings = UserSettings(user_id=user.id)
            session.add(settings)
            session.flush()

        notifications = settings_payload.get("notifications") or {}
        if "emailNotifications" in notifications:
            settings.email_notifications = notifications["emailNotifications"]
        if "campaignAlerts" in notifications:
            settings.campaign_alerts = notifications["campaignAlerts"]
        if "jobAlerts" in notifications:
            settings.job_alerts = notifications["jobAlerts"]
        if "dailyReport" in notifications:
            settings.daily_report = notifications["dailyReport"]
        if "weeklyDigest" in notifications:
            settings.weekly_digest = notifications["weeklyDigest"]
        if "smsNotifications" in notifications:
            settings.sms_notifications = notifications["smsNotifications"]
        if "smsPhone" in notifications:
            settings.sms_phone = notifications["smsPhone"] or None
        if "language" in settings_payload:
            settings.language = settings_payload["language"]
        if "dateFormat" in settings_payload:
            settings.date_format = settings_payload["dateFormat"]
        if "theme" in settings_payload:
            settings.theme = settings_payload["theme"]


def ensure_auth_ready() -> None:
    if get_engine() is None:
        return
    backend_root = Path(__file__).resolve().parents[2]
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    from scripts.init_postgres_schema import DEMO_USERS, main as seed_main

    profile_fields = ("phone", "company", "title", "department", "location", "timezone", "bio")

    with session_scope() as session:
        if session.query(User).count() == 0:
            seed_main()
            return

        for demo in DEMO_USERS:
            user = session.query(User).filter(User.email == demo["email"]).first()
            if not user:
                continue
            for field in profile_fields:
                if field in demo and demo[field] and not getattr(user, field, None):
                    setattr(user, field, demo[field])
            if not user.settings:
                session.add(UserSettings(user_id=user.id))
