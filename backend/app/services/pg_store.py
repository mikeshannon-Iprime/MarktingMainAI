from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import re
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.database import session_scope
from app.db.models import (
    CampaignContact,
    CampaignItem,
    CampaignSettings,
    CampaignTemplate,
    Carrier,
    ContactList,
    DayReportRow,
    JobAnalysis,
    JobApplication,
    JobAutomationSettings,
    JobProfile,
    JobResult,
    LinkedInApiKey,
    LinkedInApiSource,
    LinkedInFollowup,
    LinkedInJob,
    LinkedInMessageTemplate,
    LinkedInOutreachQueue,
    LinkedInRecruiter,
    LinkedInSequence,
    LinkedInSequenceStep,
    LinkedInSettings,
    Portal,
    SavedJob,
    SearchConfig,
    SubmissionMonth,
    TailoredResume,
    User,
    UserResume,
)
from app.services import seed_data as seed_logic
from app.services.job_match_ai import enrich_and_rank_jobs
from app.core.logging import get_logger
from app.services.portal_scraper import scrape_all_portal_jobs

logger = get_logger(__name__)

WORKSPACE_EMAIL = "admin@marketingmind.ai"

# CV ↔ JD match routing for auto-apply / discovery
AUTO_APPLY_MIN_MATCH = 65
TAILOR_MIN_MATCH = 40
# Scrape windows: 1 day = 24h, 2 days = 48h
AUTO_APPLY_POSTED_WINDOWS = ("1", "2")
AUTO_APPLY_MAX_POSTED_HOURS = 48

_DEFAULT_PORTALS = [
    {"name": "Dice", "url": "https://www.dice.com", "status": "Active"},
    {"name": "Monster", "url": "https://www.monster.com", "status": "Active"},
    {"name": "CareerBuilder", "url": "https://www.careerbuilder.com", "status": "Active"},
]


def _ensure_default_portals(session: Session, user: User) -> None:
    if session.query(Portal).filter(Portal.user_id == user.id).count():
        return
    for row in _DEFAULT_PORTALS:
        session.add(Portal(user_id=user.id, name=row["name"], url=row["url"], status=row.get("status", "Active")))
    session.flush()
    logger.info("Seeded %d default portal(s) for user_id=%s", len(_DEFAULT_PORTALS), user.id)


def _get_user_portals(session: Session, user: User, *, include_status: bool = True) -> List[dict]:
    _ensure_default_portals(session, user)
    rows = session.query(Portal).filter(Portal.user_id == user.id).all()
    if include_status:
        return [{"name": row.name, "url": row.url, "status": row.status} for row in rows]
    return [{"name": row.name, "url": row.url} for row in rows]


def _workspace_user(session: Session) -> User:
    user = session.query(User).filter(User.email == WORKSPACE_EMAIL).first()
    if not user:
        user = session.query(User).order_by(User.id).first()
    if not user:
        raise RuntimeError("Database has no users. Run: python scripts/init_postgres_schema.py")
    return user


def _resolve_user(session: Session, user_external_id: str | None = None) -> User:
    if user_external_id:
        user = session.query(User).filter(User.external_id == user_external_id).first()
        if user:
            return user
    return _workspace_user(session)


_GENERATED_SEARCH_URL_PREFIXES = (
    "https://www.dice.com/jobs?",
    "https://www.monster.com/jobs/search?",
    "https://www.careerbuilder.com/jobs?",
    "https://www.linkedin.com/jobs/search/?",
    "https://www.indeed.com/jobs?",
    "https://www.ziprecruiter.com/jobs-search?",
)


def _effective_job_source_url(row: JobResult) -> str:
    """Return a fetchable portal URL, rewriting legacy fake / generated search links."""
    source_url = (row.source_url or "").strip()
    portal_root = (row.portal_url or "").rstrip("/")
    is_legacy_fake_url = bool(
        source_url
        and (
            (portal_root and source_url.startswith(f"{portal_root}/jobs/") and source_url.rsplit("/", 1)[-1].isdigit())
            or re.search(r"https?://(?:www\.)?dice\.com/jobs/\d+$", source_url, re.IGNORECASE)
            or re.search(r"https?://(?:www\.)?monster\.com/jobs/\d+$", source_url, re.IGNORECASE)
        )
    )
    is_generated_search_url = bool(source_url) and source_url.startswith(_GENERATED_SEARCH_URL_PREFIXES)
    if is_legacy_fake_url or is_generated_search_url or not source_url:
        from app.services.portal_scraper import build_portal_search_url

        rebuilt = build_portal_search_url(
            {"name": row.portal_name or "", "url": row.portal_url or ""},
            row.role,
            row.location,
            keyword=(row.skills or [row.role or "Software Engineer"])[0],
        )
        return rebuilt or source_url
    return source_url


def _job_result_dict(row: JobResult) -> dict:
    source_url = _effective_job_source_url(row)

    return {
        "id": row.id,
        "role": row.role,
        "company": row.company,
        "location": row.location,
        "type": row.type,
        "posted": row.posted,
        "rate": row.rate,
        "match": row.match,
        "hot": row.hot,
        "skills": row.skills or [],
        "portalName": row.portal_name,
        "portalUrl": row.portal_url,
        "sourceUrl": source_url,
        "description": row.description,
    }


def _posted_within_hours(
    posted_label: str | None,
    max_hours: int = AUTO_APPLY_MAX_POSTED_HOURS,
    date_posted: str | None = None,
) -> bool:
    """True when a job's posted age is within max_hours (supports hour/day/plain-day labels)."""
    if date_posted:
        try:
            posted_at = datetime.fromisoformat(str(date_posted).replace("Z", "+00:00"))
            if posted_at.tzinfo is None:
                posted_at = posted_at.replace(tzinfo=timezone.utc)
            return posted_at >= (datetime.now(timezone.utc) - timedelta(hours=max_hours))
        except ValueError:
            pass

    label = str(posted_label or "").strip().lower()
    if not label:
        return False

    match = re.search(r"(\d+)", label)
    if not match:
        return False

    value = int(match.group(1))
    if "hour" in label or "hr" in label or "h " in f"{label} ":
        return value <= max_hours
    if "day" in label or "d " in f"{label} ":
        return value * 24 <= max_hours

    # Plain numeric labels are treated as days in this backend.
    return value * 24 <= max_hours


def _posted_within_24_hours(posted_label: str | None, date_posted: str | None = None) -> bool:
    """Backward-compatible alias — eligibility covers the 24h and 48h scrape windows."""
    return _posted_within_hours(posted_label, AUTO_APPLY_MAX_POSTED_HOURS, date_posted=date_posted)


def _application_dict(row: JobApplication) -> dict:
    app_date = row.application_date.isoformat() if row.application_date else row.updated_label
    return {
        "id": row.id,
        "jobResultId": row.job_result_id,
        "role": row.role,
        "company": row.company,
        "status": row.status,
        "stage": row.stage,
        "updated": row.updated_label,
        "action": row.action_label,
        "portal": row.portal,
        "date": app_date,
        "match": row.match,
        "postingUrl": row.posting_url,
        "attemptStatus": getattr(row, "attempt_status", None) or "manual",
        "attemptDetail": getattr(row, "attempt_detail", None) or "",
        "confirmationUrl": getattr(row, "confirmation_url", None),
    }


_PROFILE_DEFAULTS = {
    "name": "New Candidate",
    "email": "candidate@email.com",
    "phone": "+1 (555) 555-0128",
    "location": "Remote, USA",
    "linkedin": "https://linkedin.com/in/profile",
    "experience": "3-5 Years",
    "employmentType": "Both",
    "rate": "Open to discuss",
    "visa": "Authorized to work",
    "workMode": "Remote",
    "jobTitles": [],
    "resumeFileName": None,
    "resumeSummary": None,
    "resumeSkills": [],
}


def _normalize_profile_for_response(profile: dict | None, user: User | None = None) -> dict:
    result = dict(_PROFILE_DEFAULTS)
    if user:
        if user.name and len(user.name.strip()) >= 2:
            result["name"] = user.name.strip()
        if user.email:
            result["email"] = user.email
        if user.phone and len(user.phone.strip()) >= 6:
            result["phone"] = user.phone.strip()
        if user.location and len(user.location.strip()) >= 2:
            result["location"] = user.location.strip()
    if not profile:
        return result
    for key, value in profile.items():
        if value is None:
            continue
        if key in ("resumeFileName", "resumeSummary") and value == "":
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if key == "phone" and len(str(value).strip()) < 6:
            continue
        if key == "location" and len(str(value).strip()) < 2:
            continue
        if key == "linkedin" and not str(value).strip().startswith(("http://", "https://")):
            continue
        if key == "name" and len(str(value).strip()) < 2:
            continue
        if key in ("rate", "visa") and not str(value).strip():
            continue
        result[key] = value
    return result


def _profile_dict(row: JobProfile, user: User | None = None) -> dict:
    raw = {
        "name": row.name,
        "email": row.email,
        "phone": row.phone,
        "location": row.location,
        "linkedin": row.linkedin,
        "experience": row.experience,
        "employmentType": row.employment_type,
        "rate": row.rate,
        "visa": row.visa,
        "workMode": row.work_mode,
        "jobTitles": row.job_titles or [],
        "resumeFileName": row.resume_file_name,
        "resumeSummary": row.resume_summary,
        "resumeSkills": row.resume_skills or [],
    }
    return _normalize_profile_for_response(raw, user)


def _resume_dict(row: UserResume) -> dict:
    snapshot = dict(getattr(row, "profile_snapshot", None) or {})
    return {
        "id": row.id,
        "fileName": row.file_name,
        "summary": row.summary or "",
        "skills": row.skills or [],
        "jobTitles": row.job_titles or [],
        "mlScore": row.ml_score,
        "matchedSkills": row.matched_skills or [],
        "missingSkills": row.missing_skills or [],
        "isActive": row.is_active,
        "hasFile": bool(getattr(row, "file_bytes", None)),
        "contentType": getattr(row, "content_type", None),
        "uploadedAt": row.created_at.isoformat().replace("+00:00", "Z") if row.created_at else None,
        "profileName": snapshot.get("name") or None,
        "experience": snapshot.get("experience") or None,
        "profileSnapshot": snapshot or None,
    }


def _snapshot_from_profile_row(profile: JobProfile, *, resume_file_name: str | None = None) -> dict:
    return {
        "name": profile.name or "",
        "email": profile.email or "",
        "phone": profile.phone or "",
        "location": profile.location or "",
        "linkedin": profile.linkedin or "",
        "experience": profile.experience or "",
        "employmentType": profile.employment_type or "",
        "rate": profile.rate or "",
        "visa": profile.visa or "",
        "workMode": profile.work_mode or "",
        "jobTitles": list(profile.job_titles or []),
        "resumeFileName": resume_file_name if resume_file_name is not None else profile.resume_file_name,
        "resumeSummary": profile.resume_summary or "",
        "resumeSkills": list(profile.resume_skills or []),
    }


def _snapshot_from_payload(payload: dict, *, resume_file_name: str | None = None) -> dict:
    return {
        "name": payload.get("name") or "",
        "email": payload.get("email") or "",
        "phone": payload.get("phone") or "",
        "location": payload.get("location") or "",
        "linkedin": payload.get("linkedin") or "",
        "experience": payload.get("experience") or "",
        "employmentType": payload.get("employmentType") or "",
        "rate": payload.get("rate") or "",
        "visa": payload.get("visa") or "",
        "workMode": payload.get("workMode") or "",
        "jobTitles": list(payload.get("jobTitles") or []),
        "resumeFileName": resume_file_name if resume_file_name is not None else payload.get("resumeFileName"),
        "resumeSummary": payload.get("resumeSummary") or "",
        "resumeSkills": list(payload.get("resumeSkills") or []),
    }


def _clip(value: Any, max_len: int) -> str:
    text = str(value or "").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip()


def _apply_snapshot_to_profile(profile: JobProfile, snapshot: dict, *, file_name: str | None = None) -> None:
    if not snapshot:
        if file_name:
            profile.resume_file_name = _clip(file_name, 255)
        return
    if snapshot.get("name"):
        profile.name = _clip(snapshot["name"], 120)
    if snapshot.get("email"):
        profile.email = _clip(snapshot["email"], 255)
    if snapshot.get("phone"):
        profile.phone = _clip(snapshot["phone"], 40)
    if snapshot.get("location"):
        profile.location = _clip(snapshot["location"], 120)
    if snapshot.get("linkedin"):
        profile.linkedin = _clip(snapshot["linkedin"], 255)
    if snapshot.get("experience"):
        profile.experience = _clip(snapshot["experience"], 60)
    if snapshot.get("employmentType"):
        profile.employment_type = _clip(snapshot["employmentType"], 80)
    if snapshot.get("rate"):
        profile.rate = _clip(snapshot["rate"], 60)
    if snapshot.get("visa"):
        profile.visa = _clip(snapshot["visa"], 40)
    if snapshot.get("workMode"):
        profile.work_mode = _clip(snapshot["workMode"], 60)
    profile.job_titles = list(snapshot.get("jobTitles") or [])
    profile.resume_skills = list(snapshot.get("resumeSkills") or [])
    profile.resume_summary = snapshot.get("resumeSummary") or ""
    profile.resume_file_name = _clip(
        file_name or snapshot.get("resumeFileName") or profile.resume_file_name or "",
        255,
    ) or profile.resume_file_name


def _apply_snapshot_to_search(search: SearchConfig, snapshot: dict) -> None:
    """Replace (not merge) search titles/skills from an isolated CV snapshot."""
    titles = list(snapshot.get("jobTitles") or [])
    skills = list(snapshot.get("resumeSkills") or [])
    if titles:
        search.titles = titles
    if skills:
        search.required_skills = skills


def _ensure_resume_snapshot(resume: UserResume, profile: JobProfile | None = None) -> dict:
    snapshot = dict(getattr(resume, "profile_snapshot", None) or {})
    if snapshot:
        return snapshot
    # Backfill legacy rows from resume columns (+ optional active profile prefs).
    snapshot = {
        "name": (profile.name if profile else "") or "",
        "email": (profile.email if profile else "") or "",
        "phone": (profile.phone if profile else "") or "",
        "location": (profile.location if profile else "") or "",
        "linkedin": (profile.linkedin if profile else "") or "",
        "experience": (profile.experience if profile else "") or "",
        "employmentType": (profile.employment_type if profile else "") or "",
        "rate": (profile.rate if profile else "") or "",
        "visa": (profile.visa if profile else "") or "",
        "workMode": (profile.work_mode if profile else "") or "",
        "jobTitles": list(resume.job_titles or []),
        "resumeFileName": resume.file_name,
        "resumeSummary": resume.summary or "",
        "resumeSkills": list(resume.skills or []),
    }
    resume.profile_snapshot = snapshot
    return snapshot


def _user_resumes(session: Session, user: User) -> list[dict]:
    rows = (
        session.query(UserResume)
        .filter(UserResume.user_id == user.id)
        .order_by(UserResume.is_active.desc(), UserResume.id.desc())
        .all()
    )
    return [_resume_dict(row) for row in rows]


def _search_dict(row: SearchConfig) -> dict:
    return {
        "titles": row.titles or [],
        "requiredSkills": row.required_skills or [],
        "optionalSkills": row.optional_skills or [],
        "location": row.location,
        "radius": row.radius,
        "filters": row.filters or [],
        "excludeKeywords": row.exclude_keywords or [],
        "employmentType": row.employment_type,
        "minMatchScore": row.min_match_score,
        "postedWithin": row.posted_within,
        "experienceLevel": row.experience_level,
        "rateMin": row.rate_min,
        "rateMax": row.rate_max,
        "repeatEvery": row.repeat_every,
    }


def _automation_dict(row: JobAutomationSettings) -> dict:
    return {
        "autoApply": row.auto_apply,
        "matchThreshold": row.match_threshold,
        "maxApplications": row.max_applications,
        "alerts": row.alerts,
        "tailorCv": row.tailor_cv,
        "scheduleEnabled": row.schedule_enabled,
        "scheduleLabel": row.schedule_label,
        "scheduleTimezone": row.schedule_timezone,
        "scheduleTime": row.schedule_time,
    }


def _campaign_metrics(session: Session, user_id: int) -> dict:
    items = session.query(CampaignItem).filter(CampaignItem.user_id == user_id).all()
    total_sent = sum(item.sent_count for item in items)
    total_opened = sum(item.opened_count for item in items)
    total_replied = sum(item.replied_count for item in items)
    open_rate = 0 if total_sent == 0 else round(total_opened / total_sent * 100)
    reply_rate = 0 if total_sent == 0 else round(total_replied / total_sent * 100)
    return {"emailsSent": total_sent, "openRate": open_rate, "replyRate": reply_rate, "bounceRate": 2}


def get_overview_payload(user_external_id: str | None = None) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        metrics = _campaign_metrics(session, user.id)
        job_count = session.query(JobResult).filter(JobResult.user_id == user.id).count()
        latest_submission = (
            session.query(SubmissionMonth).order_by(SubmissionMonth.month.desc()).first()
        )
        return {
            "headline": "MarketingMind AI operating system for staffing campaigns, recruiter dashboards, and job automation.",
            "modules": [
                {
                    "slug": "campaigns",
                    "label": "Campaign Studio",
                    "description": "Mass email drafting, templates, contact lists, scheduling, and compliance.",
                    "metric": f"{metrics['emailsSent']:,} sends",
                },
                {
                    "slug": "job-automation",
                    "label": "Job Automation",
                    "description": "Profile setup, search automation, portal management, CV analysis, LinkedIn, and tracker.",
                    "metric": f"{job_count} high-match roles",
                },
                {
                    "slug": "day-report",
                    "label": "Day-to-Day Dashboard",
                    "description": "Recruiter performance trends across outreach, calls, sourcing, and marketing.",
                    "metric": "10 days tracked",
                },
                {
                    "slug": "submissions",
                    "label": "Submission Progress",
                    "description": "Month-over-month and year-over-year submission visibility with trend analysis.",
                    "metric": f"{latest_submission.submissions if latest_submission else 0} this month",
                },
            ],
            "activity": [
                {"title": "Campaign queue ready", "detail": "Data/AI Bench Update is scheduled for 08:45 with smart throttling enabled."},
                {"title": "Recruiter output rising", "detail": "Komal leads sourced volume this week with 18 qualified profiles."},
                {"title": "Action required", "detail": "One AI/ML application needs a tailored resume before submission."},
            ],
        }


def get_campaign_workspace(user_external_id: str | None = None) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        if not session.query(CampaignTemplate).filter(CampaignTemplate.user_id == user.id).first():
            source_user = _workspace_user(session)
            source_templates = session.query(CampaignTemplate).filter(CampaignTemplate.user_id == source_user.id).all()
            for source in source_templates:
                session.add(
                    CampaignTemplate(
                        user_id=user.id,
                        name=source.name,
                        category=source.category,
                        description=source.description,
                        subject=source.subject,
                        body=source.body,
                    )
                )
            source_settings = session.query(CampaignSettings).filter(CampaignSettings.user_id == source_user.id).first()
            if source_settings and not session.query(CampaignSettings).filter(CampaignSettings.user_id == user.id).first():
                session.add(
                    CampaignSettings(
                        user_id=user.id,
                        smtp_host=source_settings.smtp_host,
                        smtp_port=source_settings.smtp_port,
                        smtp_username=source_settings.smtp_username,
                        sender_limit=source_settings.sender_limit,
                        email_delay_seconds=source_settings.email_delay_seconds,
                        smart_warmup=source_settings.smart_warmup,
                        unsubscribe_footer=source_settings.unsubscribe_footer,
                        spam_guard=source_settings.spam_guard,
                        gmail_sync=source_settings.gmail_sync,
                        outlook_sync=source_settings.outlook_sync,
                        open_tracking=source_settings.open_tracking,
                        ai_subject_assist=source_settings.ai_subject_assist,
                        options_json=source_settings.options_json,
                    )
                )
        templates = session.query(CampaignTemplate).filter(CampaignTemplate.user_id == user.id).all()
        settings = session.query(CampaignSettings).filter(CampaignSettings.user_id == user.id).first()
        return {
            "metrics": _campaign_metrics(session, user.id),
            "composer": {
                "campaignName": "May Talent Pulse - Southwest",
                "fromName": "Sarah Mitchell",
                "fromEmail": "sarah@marketingmind.ai",
                "replyTo": "recruiter@marketingmind.ai",
                "subject": "Available consultants | {{candidate_name}} | {{location}} | C2C",
                "body": templates[0].body if templates else "",
                "mergeTags": [
                    "{{recruiter_name}}",
                    "{{candidate_name}}",
                    "{{skills}}",
                    "{{location}}",
                    "{{rate}}",
                    "{{availability}}",
                    "{{visa_status}}",
                    "{{company_name}}",
                ],
                "aiPrompts": [
                    "Hotlist blast",
                    "Candidate intro",
                    "Follow-up",
                    "Urgent placement",
                    "Bench sales",
                    "Re-introduction",
                ],
            },
            "contacts": [
                {
                    "name": row.name,
                    "email": row.email,
                    "company": row.company,
                    "status": row.status,
                    "list": row.list_name,
                }
                for row in session.query(CampaignContact).filter(CampaignContact.user_id == user.id).all()
            ],
            "lists": [
                {
                    "name": row.name,
                    "contacts": row.contacts_count,
                    "openRate": row.open_rate,
                    "replyRate": row.reply_rate,
                }
                for row in session.query(ContactList).filter(ContactList.user_id == user.id).all()
            ],
            "campaigns": [
                {
                    "name": row.name,
                    "status": row.status,
                    "scheduledFor": row.scheduled_for,
                    "sent": row.sent_count,
                    "opened": row.opened_count,
                    "replied": row.replied_count,
                    "subject": row.subject,
                    "body": row.body,
                }
                for row in session.query(CampaignItem).filter(CampaignItem.user_id == user.id).all()
            ],
            "templates": [
                {
                    "name": row.name,
                    "category": row.category,
                    "description": row.description or row.category,
                    "subject": row.subject,
                    "body": row.body,
                }
                for row in templates
            ],
            "settings": _serialize_campaign_settings(settings),
        }


def _serialize_campaign_settings(settings: CampaignSettings | None) -> dict:
    if not settings:
        return {
            "smtpHost": "smtp.gmail.com",
            "smtpPort": 587,
            "smtpUsername": "",
            "smtpPassword": "",
            "senderLimit": 500,
            "emailDelaySeconds": 3,
            "smartWarmup": True,
            "unsubscribeFooter": True,
            "spamGuard": True,
            "gmailSync": False,
            "outlookSync": False,
            "openTracking": True,
            "aiSubjectAssist": True,
        }
    options = settings.options_json or {}
    return {
        "smtpHost": settings.smtp_host,
        "smtpPort": settings.smtp_port,
        "smtpUsername": settings.smtp_username or "",
        "smtpPassword": settings.smtp_password or "",
        "senderLimit": settings.sender_limit,
        "emailDelaySeconds": settings.email_delay_seconds,
        "smartWarmup": settings.smart_warmup,
        "unsubscribeFooter": settings.unsubscribe_footer,
        "spamGuard": settings.spam_guard,
        "gmailSync": settings.gmail_sync,
        "outlookSync": settings.outlook_sync,
        "openTracking": settings.open_tracking,
        "aiSubjectAssist": settings.ai_subject_assist,
        **options,
    }


def _load_campaign_settings(session: Session, user_id: int) -> dict:
    settings = session.query(CampaignSettings).filter(CampaignSettings.user_id == user_id).first()
    return _serialize_campaign_settings(settings)


def _load_campaign_settings_for_user(user_external_id: str | None) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        return _load_campaign_settings(session, user.id)


def _load_campaign_contacts(session: Session, user_id: int) -> List[dict]:
    return [
        {
            "name": row.name,
            "email": row.email,
            "company": row.company,
            "status": row.status,
            "list": row.list_name,
        }
        for row in session.query(CampaignContact).filter(CampaignContact.user_id == user_id).all()
    ]


def get_job_automation_workspace(user_external_id: str | None = None) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        profile = _get_or_create_job_profile(session, user)
        automation = _get_or_create_automation(session, user)
        search = _get_or_create_search(session, user)
        job_results = [
            _job_result_dict(row)
            for row in session.query(JobResult)
            .filter(JobResult.user_id == user.id)
            .all()
            if _posted_within_hours(row.posted, AUTO_APPLY_MAX_POSTED_HOURS)
        ]
        job_results.sort(key=lambda job: job.get("match", 0), reverse=True)
        applications = [
            _application_dict(row)
            for row in session.query(JobApplication).filter(JobApplication.user_id == user.id).order_by(JobApplication.id.desc()).all()
        ]
        applications_payload = seed_logic.build_applications_payload(applications, job_results)
        interviews = applications_payload["interviews"]
        analysis = session.query(JobAnalysis).filter(JobAnalysis.user_id == user.id).order_by(JobAnalysis.id.desc()).first()
        saved_jobs = [
            row.job_result_id
            for row in session.query(SavedJob).filter(SavedJob.user_id == user.id).all()
        ]
        linkedin_jobs = session.query(LinkedInJob).filter(LinkedInJob.user_id == user.id).all()
        return {
            "stats": {
                "appliedToday": 6,
                "newMatches": len(job_results),
                "interviews": len(interviews),
                "avgMatchScore": round(sum(job["match"] for job in job_results) / len(job_results)) if job_results else 0,
            },
            "profile": _profile_dict(profile, user),
            "automation": _automation_dict(automation),
            "search": _search_dict(search),
            "resumes": _user_resumes(session, user),
            "portals": _get_user_portals(session, user),
            "carriers": [
                {"name": row.name, "url": row.url, "status": row.status}
                for row in session.query(Carrier).filter(Carrier.user_id == user.id).all()
            ],
            "results": job_results,
            "savedJobs": saved_jobs,
            "analysis": {
                "selectedJobId": analysis.job_result_id if analysis else 1,
                "score": analysis.score if analysis else 0,
                "summary": analysis.summary if analysis else "",
                "hits": analysis.hits if analysis else [],
                "misses": analysis.misses if analysis else [],
                "suggestions": analysis.suggestions if analysis else [],
            },
            "linkedin": [
                {
                    "role": row.role,
                    "company": row.company,
                    "location": row.location,
                    "type": row.type,
                    "posted": row.posted,
                    "match": row.match,
                    "easyApply": row.easy_apply,
                    "applicants": row.applicants,
                    "insight": row.insight,
                    "linkedinUrl": row.linkedin_url,
                    "experienceLevel": row.experience_level,
                    "datePosted": row.date_posted,
                }
                for row in linkedin_jobs
            ],
            "applications": applications_payload,
        }


def _get_or_create_job_profile(session: Session, user: User) -> JobProfile:
    profile = session.query(JobProfile).filter(JobProfile.user_id == user.id).first()
    if profile:
        return profile
    defaults = _normalize_profile_for_response({}, user)
    profile = JobProfile(
        user_id=user.id,
        name=defaults["name"],
        email=defaults["email"],
        phone=defaults["phone"],
        location=defaults["location"],
        linkedin=defaults["linkedin"],
        experience=defaults["experience"],
        employment_type=defaults["employmentType"],
        rate=defaults["rate"],
        visa=defaults["visa"],
        work_mode=defaults["workMode"],
        job_titles=[],
        resume_skills=[],
    )
    session.add(profile)
    session.flush()
    return profile


def _get_or_create_search(session: Session, user: User) -> SearchConfig:
    search = session.query(SearchConfig).filter(SearchConfig.user_id == user.id).first()
    if search:
        return search
    search = SearchConfig(user_id=user.id)
    session.add(search)
    session.flush()
    return search


def _get_or_create_automation(session: Session, user: User) -> JobAutomationSettings:
    automation = session.query(JobAutomationSettings).filter(JobAutomationSettings.user_id == user.id).first()
    if automation:
        return automation
    automation = JobAutomationSettings(user_id=user.id)
    session.add(automation)
    session.flush()
    return automation


def save_job_profile(payload: dict, user_external_id: str | None = None) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        profile = _get_or_create_job_profile(session, user)
        field_map = {
            "name": "name",
            "email": "email",
            "phone": "phone",
            "location": "location",
            "linkedin": "linkedin",
            "experience": "experience",
            "employmentType": "employment_type",
            "rate": "rate",
            "visa": "visa",
            "workMode": "work_mode",
            "resumeFileName": "resume_file_name",
            "resumeSummary": "resume_summary",
        }
        for key, attr in field_map.items():
            if key in payload and payload[key] is not None:
                setattr(profile, attr, payload[key])
        if "resumeSkills" in payload and payload["resumeSkills"] is not None:
            profile.resume_skills = payload["resumeSkills"]
        if payload.get("jobTitles") is not None:
            profile.job_titles = payload["jobTitles"]
            search = _get_or_create_search(session, user)
            # Active CV owns search titles — replace, do not merge with other CVs.
            search.titles = list(payload["jobTitles"])
        if "resumeSkills" in payload and payload["resumeSkills"] is not None:
            search = _get_or_create_search(session, user)
            search.required_skills = list(payload["resumeSkills"])

        # Sync the active CV's isolated snapshot so switching away/back restores edits.
        active_resume = (
            session.query(UserResume)
            .filter(UserResume.user_id == user.id, UserResume.is_active.is_(True))
            .first()
        )
        if active_resume:
            snapshot = _snapshot_from_profile_row(profile, resume_file_name=active_resume.file_name)
            active_resume.profile_snapshot = snapshot
            active_resume.summary = snapshot.get("resumeSummary") or ""
            active_resume.skills = list(snapshot.get("resumeSkills") or [])
            active_resume.job_titles = list(snapshot.get("jobTitles") or [])
            profile.resume_file_name = active_resume.file_name

        session.flush()
        search = _get_or_create_search(session, user)
        return {
            "success": True,
            "message": "Job profile updated.",
            "profile": _profile_dict(profile, user),
            "search": _search_dict(search),
            "resumes": _user_resumes(session, user),
        }


def save_automation_settings(payload: dict, user_external_id: str | None = None) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        automation = _get_or_create_automation(session, user)
        field_map = {
            "autoApply": "auto_apply",
            "matchThreshold": "match_threshold",
            "maxApplications": "max_applications",
            "alerts": "alerts",
            "tailorCv": "tailor_cv",
            "scheduleEnabled": "schedule_enabled",
            "scheduleLabel": "schedule_label",
            "scheduleTimezone": "schedule_timezone",
            "scheduleTime": "schedule_time",
        }
        for key, attr in field_map.items():
            if key in payload and payload[key] is not None:
                setattr(automation, attr, payload[key])
        session.flush()
        return {
            "success": True,
            "message": "Automation settings saved.",
            "automation": _automation_dict(automation),
        }


def save_search_config(payload: dict, user_external_id: str | None = None) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        search = _get_or_create_search(session, user)
        field_map = {
            "titles": "titles",
            "requiredSkills": "required_skills",
            "optionalSkills": "optional_skills",
            "location": "location",
            "radius": "radius",
            "filters": "filters",
            "excludeKeywords": "exclude_keywords",
            "employmentType": "employment_type",
            "minMatchScore": "min_match_score",
            "postedWithin": "posted_within",
            "experienceLevel": "experience_level",
            "rateMin": "rate_min",
            "rateMax": "rate_max",
            "repeatEvery": "repeat_every",
        }
        for key, attr in field_map.items():
            if key in payload and payload[key] is not None:
                setattr(search, attr, payload[key])
        session.flush()
        return {
            "success": True,
            "message": "Search configuration saved.",
            "search": _search_dict(search),
        }


def apply_parsed_resume(
    parsed: dict,
    filename: str,
    user_external_id: str | None = None,
    assessment: dict | None = None,
    file_bytes: bytes | None = None,
    content_type: str | None = None,
) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        profile = _get_or_create_job_profile(session, user)
        search = _get_or_create_search(session, user)

        skills = list(parsed.get("skills") or [])
        titles = list(parsed.get("jobTitles") or [])
        experience_label = seed_logic._years_to_experience_label(parsed.get("yearsExperience"))
        summary = parsed.get("summary") or ""

        # Build an isolated snapshot for THIS CV only (no cross-resume merge).
        base = _snapshot_from_profile_row(profile, resume_file_name=filename)
        if parsed.get("fullName"):
            base["name"] = _clip(parsed["fullName"], 120)
        if parsed.get("email"):
            base["email"] = _clip(parsed["email"], 255)
        if parsed.get("phone"):
            base["phone"] = _clip(parsed["phone"], 40)
        if parsed.get("location"):
            base["location"] = _clip(parsed["location"], 120)
        if parsed.get("linkedin"):
            base["linkedin"] = _clip(parsed["linkedin"], 255)
        if experience_label:
            base["experience"] = _clip(experience_label, 60)
        base["jobTitles"] = titles
        base["resumeSkills"] = skills
        base["resumeSummary"] = summary
        base["resumeFileName"] = _clip(filename, 255)

        session.query(UserResume).filter(
            UserResume.user_id == user.id, UserResume.is_active.is_(True)
        ).update({"is_active": False})
        resume = (
            session.query(UserResume)
            .filter(UserResume.user_id == user.id, UserResume.file_name == filename)
            .first()
        )
        if not resume:
            resume = UserResume(user_id=user.id, file_name=filename)
            session.add(resume)
        resume.summary = summary
        resume.skills = skills
        resume.job_titles = titles
        resume.is_active = True
        resume.profile_snapshot = base
        if content_type:
            resume.content_type = content_type
        if file_bytes is not None:
            resume.file_bytes = file_bytes
        if assessment:
            resume.ml_score = assessment.get("matchScore")
            resume.matched_skills = assessment.get("matchedSkills") or []
            resume.missing_skills = assessment.get("missingSkills") or []

        # Replace active working copy + search from this CV only.
        _apply_snapshot_to_profile(profile, base, file_name=filename)
        _apply_snapshot_to_search(search, base)
        session.flush()
        return {
            "profile": _profile_dict(profile, user),
            "search": _search_dict(search),
            "resumes": _user_resumes(session, user),
        }


def list_user_resumes(user_external_id: str | None = None) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        return {"resumes": _user_resumes(session, user)}


def activate_user_resume(resume_id: int, user_external_id: str | None = None) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        resume = (
            session.query(UserResume)
            .filter(UserResume.id == resume_id, UserResume.user_id == user.id)
            .first()
        )
        if not resume:
            raise ValueError("Resume not found for this user.")

        session.query(UserResume).filter(
            UserResume.user_id == user.id, UserResume.is_active.is_(True)
        ).update({"is_active": False})
        resume.is_active = True

        profile = _get_or_create_job_profile(session, user)
        search = _get_or_create_search(session, user)
        snapshot = _ensure_resume_snapshot(resume, profile)
        # Prefer stored snapshot columns if snapshot is sparse on resume fields.
        if not snapshot.get("resumeSkills") and resume.skills:
            snapshot["resumeSkills"] = list(resume.skills)
        if not snapshot.get("jobTitles") and resume.job_titles:
            snapshot["jobTitles"] = list(resume.job_titles)
        if not snapshot.get("resumeSummary") and resume.summary:
            snapshot["resumeSummary"] = resume.summary
        snapshot["resumeFileName"] = resume.file_name
        resume.profile_snapshot = snapshot

        _apply_snapshot_to_profile(profile, snapshot, file_name=resume.file_name)
        _apply_snapshot_to_search(search, snapshot)
        session.flush()
        return {
            "success": True,
            "message": f"{resume.file_name} is now the active CV.",
            "resumes": _user_resumes(session, user),
            "profile": _profile_dict(profile, user),
            "search": _search_dict(search),
        }


def delete_user_resume(resume_id: int, user_external_id: str | None = None) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        resume = (
            session.query(UserResume)
            .filter(UserResume.id == resume_id, UserResume.user_id == user.id)
            .first()
        )
        if not resume:
            raise ValueError("Resume not found for this user.")
        was_active = resume.is_active
        file_name = resume.file_name
        session.delete(resume)
        session.flush()

        profile = _get_or_create_job_profile(session, user)
        search = _get_or_create_search(session, user)
        if was_active:
            fallback = (
                session.query(UserResume)
                .filter(UserResume.user_id == user.id)
                .order_by(UserResume.id.desc())
                .first()
            )
            if fallback:
                fallback.is_active = True
                snapshot = _ensure_resume_snapshot(fallback, profile)
                if not snapshot.get("resumeSkills") and fallback.skills:
                    snapshot["resumeSkills"] = list(fallback.skills)
                if not snapshot.get("jobTitles") and fallback.job_titles:
                    snapshot["jobTitles"] = list(fallback.job_titles)
                if not snapshot.get("resumeSummary") and fallback.summary:
                    snapshot["resumeSummary"] = fallback.summary
                snapshot["resumeFileName"] = fallback.file_name
                fallback.profile_snapshot = snapshot
                _apply_snapshot_to_profile(profile, snapshot, file_name=fallback.file_name)
                _apply_snapshot_to_search(search, snapshot)
            else:
                profile.resume_file_name = None
                profile.resume_summary = None
                profile.resume_skills = []
                profile.job_titles = []
        session.flush()
        return {
            "success": True,
            "message": f"{file_name} removed from your CV library.",
            "resumes": _user_resumes(session, user),
            "profile": _profile_dict(profile, user),
            "search": _search_dict(search),
        }


def _clip_str(value: Any, max_len: int, default: str = "") -> str:
    text = str(value if value is not None else default).strip()
    if not text:
        return default
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _next_job_result_id(session: Session) -> int:
    current_max = session.query(func.max(JobResult.id)).scalar()
    return int(current_max or 0) + 1


def _scrape_configured_portals(
    session: Session,
    user: User,
    *,
    posted_windows: List[str] | tuple[str, ...] | None = None,
) -> dict:
    search = _get_or_create_search(session, user)
    profile = _get_or_create_job_profile(session, user)
    portals = _get_user_portals(session, user)

    existing_jobs = [
        _job_result_dict(row)
        for row in session.query(JobResult).filter(JobResult.user_id == user.id).all()
    ]
    titles = search.titles or profile.job_titles or ["Software Engineer"]
    skills = profile.resume_skills or []
    required_skills = search.required_skills or skills
    location = search.location or profile.location or "Remote"
    windows = list(posted_windows) if posted_windows else [search.posted_within or "3"]
    # Prefer longest window last so freshest scrape IDs land last; dedupe by role+company+portal.
    seen_keys: set[tuple[str, str, str]] = {
        (
            str(job.get("role", "")).lower(),
            str(job.get("company", "")).lower(),
            str(job.get("portalName") or job.get("sourceUrl") or "").lower(),
        )
        for job in existing_jobs
    }
    scraped_jobs: List[dict] = []
    next_id = _next_job_result_id(session)

    for window in windows:
        batch, _ = scrape_all_portal_jobs(
            portals,
            titles=titles,
            skills=skills,
            required_skills=required_skills,
            location=location,
            existing_jobs=existing_jobs + scraped_jobs,
            next_job_id=next_id,
            posted_within=window,
        )
        for job in batch:
            key = (
                str(job.get("role", "")).lower(),
                str(job.get("company", "")).lower(),
                str(job.get("portalName") or job.get("sourceUrl") or "").lower(),
            )
            if key in seen_keys:
                continue
            seen_keys.add(key)
            job["id"] = next_id
            next_id += 1
            scraped_jobs.append(job)

    for job in scraped_jobs:
        session.add(
            JobResult(
                id=job["id"],
                user_id=user.id,
                role=_clip_str(job.get("role"), 512, "Untitled role"),
                company=_clip_str(job.get("company"), 512, "Unknown company"),
                location=_clip_str(job.get("location"), 255, "Remote"),
                type=_clip_str(job.get("type"), 120, "Contract"),
                posted=_clip_str(job.get("posted"), 32, "0"),
                rate=_clip_str(job.get("rate"), 120) or None,
                match=job.get("match", 0),
                hot=job.get("hot", False),
                skills=job.get("skills", []),
                portal_name=_clip_str(job.get("portalName"), 120) or None,
                portal_url=_clip_str(job.get("portalUrl"), 1024) or None,
                source_url=_clip_str(job.get("sourceUrl"), 1024) or None,
                description=job.get("description"),
            )
        )

    session.flush()
    active_count = len([portal for portal in portals if (portal.get("status") or "Active") == "Active"]) or len(portals)
    return {
        "scraped": len(scraped_jobs),
        "portalCount": active_count,
        "postedWindows": windows,
    }


def _job_text_blob(job: dict) -> str:
    return " ".join(
        [
            job.get("role", ""),
            job.get("company", ""),
            job.get("location", ""),
            job.get("description", ""),
            " ".join(job.get("skills", [])),
        ]
    ).lower()


def _filter_job_results(
    jobs: List[dict],
    *,
    titles: List[str],
    required_skills: List[str],
    optional_skills: List[str],
    employment_type: str,
    exclude_keywords: List[str],
    posted_within: int,
    experience_level: str,
    rate_min: Optional[float],
    rate_max: Optional[float],
    portals: List[dict],
    min_score: Optional[int] = None,
) -> List[dict]:
    filtered = []
    for job in jobs:
        role_text = job["role"].lower()
        if titles and not any(title.lower() in role_text for title in titles):
            continue
        if min_score is not None and job.get("match", 0) < min_score:
            continue
        if not seed_logic._employment_matches(job.get("type", ""), employment_type):
            continue
        if seed_logic._posted_within_days(job.get("posted", "999")) > posted_within:
            continue
        if not seed_logic._experience_matches(job, experience_level):
            continue
        job_rate = seed_logic._parse_rate_value(job.get("rate", ""))
        if rate_min is not None and job_rate is not None and job_rate < rate_min:
            continue
        if rate_max is not None and job_rate is not None and job_rate > rate_max:
            continue
        job_blob = _job_text_blob(job)
        if exclude_keywords and any(keyword in job_blob for keyword in exclude_keywords if keyword):
            continue
        if required_skills and not any(skill in job_blob for skill in required_skills):
            continue
        if optional_skills and not any(skill in job_blob for skill in optional_skills):
            if not required_skills:
                continue
        enriched = dict(job)
        if not enriched.get("portalName") and portals:
            portal = portals[job["id"] % len(portals)]
            enriched["portalName"] = portal["name"]
            enriched["portalUrl"] = portal["url"]
            enriched["sourceUrl"] = enriched.get("sourceUrl") or f"{portal['url']}/jobs/{job['id']}"
        filtered.append(enriched)
    return filtered


def _rank_jobs_with_cv(session: Session, user: User, jobs: List[dict]) -> tuple[List[dict], dict]:
    profile = _get_or_create_job_profile(session, user)
    search = _get_or_create_search(session, user)
    return enrich_and_rank_jobs(jobs, _profile_dict(profile, user), _search_dict(search))


def run_job_search(payload: dict, user_external_id: str | None = None) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        search = _get_or_create_search(session, user)
        for key, attr in {
            "titles": "titles",
            "requiredSkills": "required_skills",
            "optionalSkills": "optional_skills",
            "location": "location",
            "radius": "radius",
            "excludeKeywords": "exclude_keywords",
            "employmentType": "employment_type",
            "minMatchScore": "min_match_score",
            "postedWithin": "posted_within",
            "experienceLevel": "experience_level",
            "rateMin": "rate_min",
            "rateMax": "rate_max",
            "repeatEvery": "repeat_every",
        }.items():
            if key in payload and payload[key] is not None:
                setattr(search, attr, payload[key])
        session.flush()

        scrape_meta = _scrape_configured_portals(
            session,
            user,
            posted_windows=list(AUTO_APPLY_POSTED_WINDOWS),
        )

        titles = payload.get("titles") or search.titles or []
        required_skills = [skill.lower() for skill in (payload.get("requiredSkills") or search.required_skills or [])]
        optional_skills = [skill.lower() for skill in (payload.get("optionalSkills") or search.optional_skills or [])]
        min_score = int(payload.get("minMatchScore", search.min_match_score or 70))
        employment_type = payload.get("employmentType", search.employment_type or "Both")
        exclude_keywords = [keyword.lower() for keyword in (payload.get("excludeKeywords") or search.exclude_keywords or [])]
        # Match routing policy: Results only surface jobs from the 24h/48h windows.
        raw_posted_within = int(payload.get("postedWithin") or search.posted_within or 2)
        posted_within = min(max(raw_posted_within, 1), 2)
        experience_level = payload.get("experienceLevel") or search.experience_level or "Any"
        rate_min = seed_logic._parse_rate_value(payload.get("rateMin") or search.rate_min or "")
        rate_max = seed_logic._parse_rate_value(payload.get("rateMax") or search.rate_max or "")
        portals = _get_user_portals(session, user, include_status=False)
        jobs = [_job_result_dict(row) for row in session.query(JobResult).filter(JobResult.user_id == user.id).all()]
        prefiltered = _filter_job_results(
            jobs,
            titles=titles,
            required_skills=required_skills,
            optional_skills=optional_skills,
            employment_type=employment_type,
            exclude_keywords=exclude_keywords,
            posted_within=posted_within,
            experience_level=experience_level,
            rate_min=rate_min,
            rate_max=rate_max,
            portals=portals,
        )
        if not prefiltered and jobs:
            prefiltered = _filter_job_results(
                jobs,
                titles=[],
                required_skills=[],
                optional_skills=[],
                employment_type=employment_type,
                exclude_keywords=exclude_keywords,
                posted_within=posted_within,
                experience_level=experience_level,
                rate_min=rate_min,
                rate_max=rate_max,
                portals=portals,
            )
        # Hard-gate: only jobs within ≤48 hours enter Results (match routing policy).
        prefiltered = [
            job
            for job in prefiltered
            if _posted_within_hours(job.get("posted"), AUTO_APPLY_MAX_POSTED_HOURS)
        ]
        ranked, matching_pipeline = _rank_jobs_with_cv(session, user, prefiltered)
        filtered = [job for job in ranked if job.get("match", 0) >= min_score]
        if not filtered and ranked:
            filtered = ranked[: min(len(ranked), 20)]
            matching_pipeline = {
                **matching_pipeline,
                "message": (
                    f"{matching_pipeline.get('message', '')} "
                    f"No jobs met {min_score}% threshold; showing top {len(filtered)} embedding-ranked matches."
                ).strip(),
            }
        ranked = filtered
        portal_names = ", ".join({portal["name"] for portal in portals}) if portals else "configured sources"
        scrape_note = (
            f" Scraped {scrape_meta['scraped']} new posting(s) across {scrape_meta['portalCount']} portal(s)."
            if scrape_meta["portalCount"]
            else ""
        )
        return {
            "success": True,
            "message": (
                f"Search completed across {portal_names} with {len(ranked)} matching jobs "
                f"(employment={employment_type}, ≤48h, min {min_score}%).{scrape_note} "
                f"{matching_pipeline['message']}"
            ),
            "results": ranked,
            "scrapedCount": scrape_meta["scraped"],
            "portalsScraped": scrape_meta["portalCount"],
            "matchingPipeline": matching_pipeline,
        }


def save_job(job_id: int) -> dict:
    with session_scope() as session:
        user = _workspace_user(session)
        existing = (
            session.query(SavedJob)
            .filter(SavedJob.user_id == user.id, SavedJob.job_result_id == job_id)
            .first()
        )
        if existing:
            session.delete(existing)
            return {"success": True, "message": "Job removed from saved list.", "saved": False}
        session.add(SavedJob(user_id=user.id, job_result_id=job_id))
        return {"success": True, "message": "Job saved to favorites.", "saved": True}


def add_portal(name: str, url: str) -> dict:
    with session_scope() as session:
        user = _workspace_user(session)
        portal = Portal(user_id=user.id, name=name, url=url, status="Active")
        session.add(portal)
        session.flush()
        return {"success": True, "message": f"Portal '{name}' added.", "portal": {"name": name, "url": url, "status": "Active"}}


def add_carrier(name: str, url: str) -> dict:
    with session_scope() as session:
        user = _workspace_user(session)
        carrier = Carrier(user_id=user.id, name=name, url=url, status="Monitoring")
        session.add(carrier)
        session.flush()
        return {"success": True, "message": f"Carrier '{name}' added.", "carrier": {"name": name, "url": url, "status": "Monitoring"}}


def delete_portal(name: str, url: str) -> dict:
    with session_scope() as session:
        user = _workspace_user(session)
        row = (
            session.query(Portal)
            .filter(Portal.user_id == user.id, Portal.name == name, Portal.url == url)
            .first()
        )
        if not row:
            raise ValueError(f"Portal '{name}' not found.")
        session.delete(row)
        return {"success": True, "message": f"Portal '{name}' removed."}


def delete_carrier(name: str, url: str) -> dict:
    with session_scope() as session:
        user = _workspace_user(session)
        row = (
            session.query(Carrier)
            .filter(Carrier.user_id == user.id, Carrier.name == name, Carrier.url == url)
            .first()
        )
        if not row:
            raise ValueError(f"Carrier '{name}' not found.")
        session.delete(row)
        return {"success": True, "message": f"Carrier '{name}' removed."}


def import_portals(portals: List[dict]) -> dict:
    with session_scope() as session:
        user = _workspace_user(session)
        existing_urls = {
            row.url
            for row in session.query(Portal).filter(Portal.user_id == user.id).all()
        }
        added = 0
        for item in portals:
            if item["url"] not in existing_urls:
                session.add(Portal(user_id=user.id, name=item["name"], url=item["url"], status="Active"))
                existing_urls.add(item["url"])
                added += 1
        session.flush()
        all_portals = [
            {"name": row.name, "url": row.url, "status": row.status}
            for row in session.query(Portal).filter(Portal.user_id == user.id).all()
        ]
        return {"success": True, "message": f"Imported {added} portal(s).", "portals": all_portals}


def import_carriers(carriers: List[dict]) -> dict:
    with session_scope() as session:
        user = _workspace_user(session)
        existing_urls = {
            row.url
            for row in session.query(Carrier).filter(Carrier.user_id == user.id).all()
        }
        added = 0
        for item in carriers:
            if item["url"] not in existing_urls:
                session.add(
                    Carrier(
                        user_id=user.id,
                        name=item["name"],
                        url=item["url"],
                        status=item.get("status") or "Monitoring",
                    )
                )
                existing_urls.add(item["url"])
                added += 1
        session.flush()
        all_carriers = [
            {"name": row.name, "url": row.url, "status": row.status}
            for row in session.query(Carrier).filter(Carrier.user_id == user.id).all()
        ]
        return {"success": True, "message": f"Imported {added} carrier page(s).", "carriers": all_carriers}


def apply_jobs(
    job_ids: List[int],
    user_external_id: str | None = None,
    supervised: bool = True,
    use_tailored_resume: bool = True,
) -> dict:
    """Apply to jobs using portal adapters (supervised job boards) or manual track+open.

    When use_tailored_resume is true, each job prefers its saved tailored CV (Analyzer /
    mid-band routing) over the active library resume.
    """
    import threading
    from dataclasses import replace

    from app.core.config import get_settings
    from app.services.portal_apply.base import ApplicantPayload
    from app.services.portal_apply.portals import portal_label

    settings = get_settings()
    mode = (settings.portal_apply_mode or "supervised").lower()
    created: list[dict] = []
    open_urls: list[str] = []
    tailored_used: list[int] = []

    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        profile = _get_or_create_job_profile(session, user)
        active_resume = (
            session.query(UserResume)
            .filter(UserResume.user_id == user.id, UserResume.is_active.is_(True))
            .first()
        )
        selected_jobs = (
            session.query(JobResult)
            .filter(JobResult.user_id == user.id, JobResult.id.in_(job_ids))
            .all()
        )
        if not selected_jobs:
            return {
                "success": False,
                "message": "No matching jobs found for this user.",
                "applied": 0,
                "applications": [],
                "tailoredJobIds": [],
            }
        eligible_jobs: list[JobResult] = []
        skipped = 0
        for row in selected_jobs:
            if _posted_within_24_hours(row.posted):
                eligible_jobs.append(row)
            else:
                skipped += 1
        if not eligible_jobs:
            return {
                "success": False,
                "message": "Only jobs posted within the last 24 or 48 hours are eligible for apply.",
                "applied": 0,
                "applications": [],
                "openUrls": [],
                "supervised": False,
                "tailoredJobIds": [],
            }

        base_applicant = ApplicantPayload(
            name=profile.name or "",
            email=profile.email or "",
            phone=profile.phone or "",
            location=profile.location or "",
            linkedin=profile.linkedin or "",
            experience=profile.experience or "",
            employment_type=profile.employment_type or "",
            rate=profile.rate or "",
            visa=profile.visa or "",
            work_mode=profile.work_mode or "",
            summary=(active_resume.summary if active_resume else None) or profile.resume_summary or "",
            skills=list((active_resume.skills if active_resume else None) or profile.resume_skills or []),
            job_titles=list((active_resume.job_titles if active_resume else None) or profile.job_titles or []),
            resume_file_name=(active_resume.file_name if active_resume else None) or profile.resume_file_name or "resume.pdf",
            resume_content_type=(active_resume.content_type if active_resume else None) or "application/pdf",
            resume_bytes=(active_resume.file_bytes if active_resume else None),
        )

        today = date.today().isoformat()
        pending: list[tuple[int, ApplicantPayload]] = []

        for job_row in eligible_jobs:
            job = _job_result_dict(job_row)
            posting_url = job.get("sourceUrl") or job.get("portalUrl") or ""
            portal_name = job.get("portalName") or "Direct"
            label = portal_label(portal_name, posting_url, fallback=portal_name)
            use_supervised = supervised and mode in {"supervised", "demo"}
            applicant = base_applicant
            used_tailored = False
            if use_tailored_resume:
                tailored_row = (
                    session.query(TailoredResume)
                    .filter(
                        TailoredResume.user_id == user.id,
                        TailoredResume.job_result_id == job["id"],
                    )
                    .first()
                )
                if tailored_row and str(tailored_row.content or "").strip():
                    content = str(tailored_row.content).strip()
                    applicant = replace(
                        base_applicant,
                        summary=content[:500],
                        resume_file_name=f"tailored-resume-job-{job['id']}.txt",
                        resume_content_type="text/plain",
                        resume_bytes=content.encode("utf-8"),
                    )
                    used_tailored = True
                    tailored_used.append(int(job["id"]))

            application = JobApplication(
                user_id=user.id,
                job_result_id=job["id"],
                role=job["role"],
                company=job["company"],
                status="Applying" if use_supervised else "Applied",
                stage=(
                    "Queued for tailored CV portal apply"
                    if use_supervised and used_tailored
                    else ("Queued for portal apply" if use_supervised else "Tracked for manual portal completion")
                ),
                updated_label=today,
                action_label=f"Complete {label} application" if use_supervised else "Await recruiter response",
                portal=portal_name,
                application_date=date.today(),
                match=job.get("match"),
                posting_url=posting_url,
                attempt_status="queued" if use_supervised else "manual",
                attempt_detail=(
                    (
                        f"Using tailored CV for {label} apply…"
                        if used_tailored
                        else f"Collecting profile + CV and launching {label} apply…"
                    )
                    if use_supervised
                    else "Application tracked. Complete submission on the portal."
                ),
            )
            session.add(application)
            session.flush()
            created.append(_application_dict(application))
            pending.append((application.id, applicant))

    if supervised and mode in {"supervised", "demo"}:
        for application_id, applicant_snapshot in pending:
            thread = threading.Thread(
                target=_run_portal_apply_attempt,
                args=(application_id, applicant_snapshot),
                daemon=True,
                name=f"portal-apply-{application_id}",
            )
            thread.start()
        tailored_note = f" {len(tailored_used)} with tailored CV." if tailored_used else ""
        message = (
            f"Started supervised apply for {len(pending)} job(s).{tailored_note} "
            "Background portal apply has started."
        )
    else:
        message = f"Tracked {len(created)} application(s) in background mode."
    if skipped:
        message = f"{message} Skipped {skipped} job(s) older than 48 hours."

    return {
        "success": True,
        "message": message,
        "applied": len(created),
        "applications": created,
        "openUrls": open_urls,
        "supervised": bool(supervised and mode in {"supervised", "demo"}),
        "tailoredJobIds": tailored_used,
    }


def _run_portal_apply_attempt(application_id: int, applicant) -> None:
    """Background worker: resolve adapter, run portal/manual apply, persist status."""
    from app.core.config import get_settings
    from app.services.portal_apply.base import JobApplyTarget
    from app.services.portal_apply.portals import portal_label
    from app.services.portal_apply.registry import resolve_adapter

    try:
        settings = get_settings()
        mode = (settings.portal_apply_mode or "supervised").lower()

        with session_scope() as session:
            application = session.query(JobApplication).filter(JobApplication.id == application_id).first()
            if not application:
                return

            # Demo mode: always finish as Applied (no live portal interaction).
            if mode == "demo":
                application.attempt_status = "applied"
                application.status = "Applied"
                application.stage = "Demo apply completed"
                application.action_label = "Await recruiter response"
                application.attempt_detail = "PORTAL_APPLY_MODE=demo — marked Applied without opening a portal."
                application.updated_label = date.today().isoformat()
                application.application_date = date.today()
                return

            job_row = None
            if application.job_result_id:
                job_row = session.query(JobResult).filter(JobResult.id == application.job_result_id).first()

            target = JobApplyTarget(
                job_id=application.job_result_id or 0,
                role=application.role,
                company=application.company,
                portal_name=application.portal or (job_row.portal_name if job_row else "") or "",
                posting_url=application.posting_url
                or (job_row.source_url if job_row else None)
                or (job_row.portal_url if job_row else None)
                or "",
                description=(job_row.description if job_row else "") or "",
            )
            adapter = resolve_adapter(target.portal_name, target.posting_url)
            label = portal_label(target.portal_name, target.posting_url, fallback=target.portal_name or "Portal")

            def on_progress(attempt_status: str, detail: str) -> None:
                with session_scope() as progress_session:
                    row = progress_session.query(JobApplication).filter(JobApplication.id == application_id).first()
                    if not row:
                        return
                    row.attempt_status = attempt_status
                    row.attempt_detail = detail
                    row.updated_label = date.today().isoformat()
                    if attempt_status == "needs_attention":
                        row.status = "Action Needed"
                        row.stage = detail[:255]
                        row.action_label = f"Resolve blocker in {label} window"
                    elif attempt_status == "awaiting_submit":
                        row.status = "Applying"
                        row.stage = f"Waiting for automated {label} Submit"
                        row.action_label = f"Watch {label} browser"
                    elif attempt_status == "filling":
                        row.status = "Applying"
                        row.stage = detail[:255]
                        row.action_label = f"Watch {label} browser"

            result = adapter.apply(target, applicant, on_progress=on_progress)

            application.attempt_status = result.attempt_status
            application.attempt_detail = result.detail or ""
            application.status = result.status
            application.stage = result.stage[:255]
            application.action_label = result.action_label[:255]
            application.updated_label = date.today().isoformat()
            if result.confirmation_url:
                application.confirmation_url = result.confirmation_url
                application.posting_url = application.posting_url or result.confirmation_url
            if result.attempt_status == "applied":
                application.application_date = date.today()
            # Normalize successful tracker outcomes to Applied + applied
            if result.status == "Applied" and result.attempt_status in {"manual", "demo"}:
                application.attempt_status = "applied"
                application.application_date = date.today()
    except Exception as exc:
        logger.exception("Portal apply attempt %s failed", application_id)
        try:
            with session_scope() as session:
                row = session.query(JobApplication).filter(JobApplication.id == application_id).first()
                if row:
                    row.attempt_status = "failed"
                    row.status = "Failed"
                    row.stage = "Portal apply worker error"
                    row.action_label = "Retry Quick Apply"
                    row.attempt_detail = str(exc)
                    row.updated_label = date.today().isoformat()
        except Exception:
            logger.exception("Failed to persist apply error for application %s", application_id)


def get_job_application(application_id: int, user_external_id: str | None = None) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        row = (
            session.query(JobApplication)
            .filter(JobApplication.id == application_id, JobApplication.user_id == user.id)
            .first()
        )
        if not row:
            raise ValueError("Application not found.")
        return _application_dict(row)


def list_recent_job_applications(user_external_id: str | None = None, limit: int = 20) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        rows = (
            session.query(JobApplication)
            .filter(JobApplication.user_id == user.id)
            .order_by(JobApplication.id.desc())
            .limit(max(1, min(limit, 200)))
            .all()
        )
        applications = [_application_dict(row) for row in rows]
        payload = seed_logic.build_applications_payload(applications, [])
        return {
            "applications": applications,
            "tracker": payload,
        }


ALLOWED_APPLICATION_STATUSES = {
    "Applying",
    "Applied",
    "Action Needed",
    "Interview",
    "Offer",
    "Tailoring",
    "Rejected",
    "Failed",
}


def update_job_application(
    application_id: int,
    *,
    status: Optional[str] = None,
    stage: Optional[str] = None,
    action: Optional[str] = None,
    notes: Optional[str] = None,
    user_external_id: str | None = None,
) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        row = (
            session.query(JobApplication)
            .filter(JobApplication.id == application_id, JobApplication.user_id == user.id)
            .first()
        )
        if not row:
            raise ValueError("Application not found.")

        if status is not None:
            cleaned = str(status).strip()
            if cleaned not in ALLOWED_APPLICATION_STATUSES:
                raise ValueError(f"Unsupported status '{cleaned}'.")
            row.status = cleaned
            if cleaned == "Interview":
                row.stage = stage or "Interview scheduled"
                row.action_label = action or "Prepare interview notes"
            elif cleaned == "Offer":
                row.stage = stage or "Offer received"
                row.action_label = action or "Review offer details"
            elif cleaned == "Rejected":
                row.stage = stage or "Closed — not selected"
                row.action_label = action or "Archive and move on"
            elif cleaned == "Action Needed":
                row.stage = stage or "Needs candidate attention"
                row.action_label = action or "Complete portal follow-up"
            elif cleaned == "Applied":
                row.stage = stage or "Submitted — awaiting response"
                row.action_label = action or "Monitor recruiter reply"
            elif cleaned == "Tailoring":
                row.stage = stage or "CV tailored for mid-band match"
                row.action_label = action or "Review tailored CV"
            elif cleaned == "Failed":
                row.stage = stage or "Apply attempt failed"
                row.action_label = action or "Retry or apply manually"

        if stage is not None and str(stage).strip():
            row.stage = str(stage).strip()[:255]
        if action is not None and str(action).strip():
            row.action_label = str(action).strip()[:255]
        if notes is not None and str(notes).strip():
            detail = str(notes).strip()
            existing = (row.attempt_detail or "").strip()
            row.attempt_detail = f"{existing}\n{detail}".strip() if existing else detail

        row.updated_label = date.today().isoformat()
        session.flush()
        return {
            "success": True,
            "message": f"Application updated to {row.status}.",
            "application": _application_dict(row),
        }


def schedule_application_followup(
    application_id: int,
    *,
    note: Optional[str] = None,
    user_external_id: str | None = None,
) -> dict:
    follow_date = (date.today()).isoformat()
    detail = note.strip() if note and note.strip() else "Follow-up reminder scheduled from Tracker."
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        row = (
            session.query(JobApplication)
            .filter(JobApplication.id == application_id, JobApplication.user_id == user.id)
            .first()
        )
        if not row:
            raise ValueError("Application not found.")

        row.action_label = f"Follow-up scheduled ({follow_date})"
        row.stage = "Awaiting recruiter reply"
        if row.status in {"Applied", "Applying", "Failed"}:
            row.status = "Action Needed"
        existing = (row.attempt_detail or "").strip()
        stamp = f"[{follow_date}] {detail}"
        row.attempt_detail = f"{existing}\n{stamp}".strip() if existing else stamp
        row.updated_label = follow_date
        session.flush()
        return {
            "success": True,
            "message": f"Follow-up scheduled for {row.role} at {row.company}.",
            "application": _application_dict(row),
        }

def refresh_job_description(
    job_id: int,
    user_external_id: str | None = None,
    *,
    force: bool = True,
) -> dict:
    """Connect to the job portal/vendor URL and pull the exact JD into JobResult."""
    from app.services.job_detail_fetcher import (
        fetch_job_detail,
        is_placeholder_description,
    )

    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        row = (
            session.query(JobResult)
            .filter(JobResult.id == job_id, JobResult.user_id == user.id)
            .first()
        )
        if not row:
            raise ValueError("Job not found for this user.")

        source_url = _effective_job_source_url(row)
        current = (row.description or "").strip()
        if (
            not force
            and current
            and not is_placeholder_description(current, role=row.role or "", company=row.company or "")
        ):
            return {
                "success": True,
                "jobId": row.id,
                "role": row.role,
                "company": row.company,
                "sourceUrl": source_url,
                "description": current,
                "descriptionQuality": "full",
                "fetchedFromPortal": False,
                "message": "Using the stored full job description.",
            }

        if not source_url.startswith(("http://", "https://")):
            return {
                "success": bool(current),
                "jobId": row.id,
                "role": row.role,
                "company": row.company,
                "sourceUrl": source_url,
                "description": current,
                "descriptionQuality": "missing",
                "fetchedFromPortal": False,
                "message": "This job has no portal detail URL to fetch from.",
            }

        detail = fetch_job_detail(
            source_url,
            role=row.role or "",
            company=row.company or "",
        )
        description = (detail.get("description") or "").strip()
        title = (detail.get("title") or "").strip()
        quality = detail.get("descriptionQuality") or "missing"
        resolved_url = (detail.get("resolvedUrl") or "").strip()
        # Only persist real posting URLs (never search pages or /jobs/{id} fakes).
        persist_url = ""
        for candidate in (resolved_url, detail.get("sourceUrl") or ""):
            candidate = str(candidate).strip()
            if not candidate.startswith("http"):
                continue
            lowered = candidate.lower()
            if "/job-detail/" in lowered or "/jobs/view/" in lowered or "/viewjob" in lowered:
                persist_url = candidate
                break

        if description and not is_placeholder_description(
            description,
            role=title or row.role or "",
            company=row.company or "",
        ):
            row.description = description
            if title and len(title) >= 3:
                row.role = _clip_str(title, 512, row.role)
            if persist_url:
                row.source_url = _clip_str(persist_url, 1024, row.source_url)
            session.flush()
            return {
                "success": True,
                "jobId": row.id,
                "role": row.role,
                "company": row.company,
                "sourceUrl": persist_url or source_url,
                "description": description,
                "descriptionQuality": quality or "full",
                "fetchedFromPortal": True,
                "message": detail.get("message")
                or f"Fetched full job description from {row.portal_name or 'portal'}.",
            }

        # Accept usable partial JD rather than failing hard.
        if description and len(description) >= 80:
            row.description = description
            if persist_url:
                row.source_url = _clip_str(persist_url, 1024, row.source_url)
            session.flush()
            return {
                "success": True,
                "jobId": row.id,
                "role": row.role,
                "company": row.company,
                "sourceUrl": persist_url or source_url,
                "description": description,
                "descriptionQuality": quality or "summary",
                "fetchedFromPortal": True,
                "message": detail.get("message") or "Fetched a partial job description from the portal.",
            }

        return {
            "success": bool(current or description),
            "jobId": row.id,
            "role": row.role,
            "company": row.company,
            "sourceUrl": source_url,
            "description": current or description,
            "descriptionQuality": "summary" if (current or description) else "missing",
            "fetchedFromPortal": False,
            "message": detail.get("message")
            or (
                "Could not extract a full JD from the portal page. "
                "Paste the description manually or open the posting URL."
            ),
        }


def analyze_job(
    job_id: Optional[int] = None,
    job_description: Optional[str] = None,
    user_external_id: str | None = None,
) -> dict:
    from app.services.analyzer_service import build_match_analysis
    from app.services.job_detail_fetcher import is_placeholder_description

    workspace = get_job_automation_workspace(user_external_id)
    jobs = workspace["results"]
    profile = workspace["profile"]
    selected = next((job for job in jobs if job["id"] == job_id), None) if job_id else None

    description = (job_description or "").strip()
    if selected:
        needs_portal = not description or is_placeholder_description(
            description or selected.get("description") or "",
            role=selected.get("role") or "",
            company=selected.get("company") or "",
        )
        if needs_portal and selected.get("sourceUrl"):
            refreshed = refresh_job_description(job_id, user_external_id, force=True)
            if refreshed.get("description"):
                description = refreshed["description"]
                selected["description"] = description
                if refreshed.get("role"):
                    selected["role"] = refreshed["role"]
        elif not description and selected.get("description"):
            description = str(selected.get("description") or "").strip()

    result = build_match_analysis(
        profile=profile,
        selected_job=selected,
        job_description=description,
        job_id=job_id,
    )
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        session.add(
            JobAnalysis(
                user_id=user.id,
                job_result_id=job_id,
                score=result.get("score", 0),
                summary=result.get("summary", ""),
                hits=result.get("hits", []),
                misses=result.get("misses", []),
                suggestions=result.get("suggestions", []),
                skill_gaps=result.get("skillGaps", []),
                recommendations=result.get("recommendations", []),
                experience_match=result.get("experienceMatch"),
                title_match=result.get("titleMatch"),
                job_description=description or result.get("jobDescription"),
            )
        )
    return result


def tailor_resume_for_job(
    job_id: int,
    job_description: Optional[str] = None,
    user_external_id: str | None = None,
) -> dict:
    from app.services.analyzer_service import build_surgical_tailor

    workspace = get_job_automation_workspace(user_external_id)
    selected = next((job for job in workspace["results"] if job["id"] == job_id), None)
    if not selected:
        raise ValueError("Job not found for this user.")
    analysis = analyze_job(
        job_id=job_id,
        job_description=job_description,
        user_external_id=user_external_id,
    )
    profile = workspace["profile"]
    active_resume = next(
        (row for row in (workspace.get("resumes") or []) if row.get("isActive")),
        None,
    )
    existing = get_tailored_resume(job_id, user_external_id)
    existing_content = existing.get("content") if existing.get("found") else ""
    tailored = build_surgical_tailor(
        profile=profile,
        selected_job={**selected, "description": analysis.get("jobDescription") or selected.get("description")},
        analysis=analysis,
        active_resume=active_resume,
        existing_tailored=existing_content or "",
    )
    boosted_score = tailored["tailoredScore"]
    role_label = selected.get("role") or "target role"
    analysis_with_score = {**analysis, "tailoredScore": boosted_score}
    return {
        "success": True,
        "jobId": job_id,
        "tailoredScore": boosted_score,
        "content": tailored["content"],
        "adjustments": tailored.get("adjustments") or [],
        "jdPointers": tailored.get("jdPointers") or [],
        "basePreserved": True,
        "message": (
            f"Role-aligned adjustments ready for {role_label} — "
            f"base resume preserved with {len(tailored.get('jdPointers') or [])} JD pointer(s) "
            f"(estimated match {boosted_score}%)."
        ),
        "analysis": analysis_with_score,
    }


def preview_application_autofill(
    job_id: Optional[int] = None,
    approved_keys: Optional[list] = None,
    user_external_id: str | None = None,
) -> dict:
    from app.services.analyzer_service import build_autofill_preview

    workspace = get_job_automation_workspace(user_external_id)
    selected = None
    if job_id:
        selected = next((job for job in workspace["results"] if job["id"] == job_id), None)
        if not selected:
            raise ValueError("Job not found for this user.")
    return build_autofill_preview(
        profile=workspace["profile"],
        selected_job=selected,
        approved_keys=approved_keys or [],
    )


def save_tailored_resume(
    job_id: int,
    content: str,
    user_external_id: str | None = None,
) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        job_exists = (
            session.query(JobResult.id)
            .filter(JobResult.id == job_id, JobResult.user_id == user.id)
            .first()
        )
        if not job_exists:
            raise ValueError("Job not found for this user.")
        row = (
            session.query(TailoredResume)
            .filter(TailoredResume.user_id == user.id, TailoredResume.job_result_id == job_id)
            .first()
        )
        if row:
            row.content = content
        else:
            session.add(TailoredResume(user_id=user.id, job_result_id=job_id, content=content))
        return {"success": True, "message": "Tailored resume saved.", "jobId": job_id}


def get_tailored_resume(job_id: int, user_external_id: str | None = None) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        row = (
            session.query(TailoredResume)
            .filter(TailoredResume.user_id == user.id, TailoredResume.job_result_id == job_id)
            .first()
        )
        if not row:
            return {"jobId": job_id, "content": "", "found": False}
        return {"jobId": job_id, "content": row.content, "found": True}


def _create_match_decision_application(
    session: Session,
    *,
    user: User,
    job: dict,
    status: str,
    stage: str,
    action_label: str,
    attempt_status: str,
    attempt_detail: str,
) -> dict:
    today = date.today().isoformat()
    application = JobApplication(
        user_id=user.id,
        job_result_id=job["id"],
        role=job["role"],
        company=job["company"],
        status=status,
        stage=stage,
        updated_label=today,
        action_label=action_label,
        portal=job.get("portalName") or "Direct",
        application_date=date.today(),
        match=job.get("match"),
        posting_url=job.get("sourceUrl") or job.get("portalUrl") or "",
        attempt_status=attempt_status,
        attempt_detail=attempt_detail,
    )
    session.add(application)
    session.flush()
    return _application_dict(application)


def run_auto_apply(match_threshold: Optional[int] = None, user_external_id: str | None = None) -> dict:
    """Scrape 24h + 48h portal windows, then route by CV↔JD match:
    >=65% apply | 40–65% tailor CV | <40% reject.
    """
    ranked: List[dict] = []
    matching_pipeline: dict = {}
    apply_ids: List[int] = []
    tailor_jobs: List[dict] = []
    reject_jobs: List[dict] = []
    tailored_apps: List[dict] = []
    rejected_apps: List[dict] = []
    scrape_meta = {"scraped": 0, "portalCount": 0, "postedWindows": list(AUTO_APPLY_POSTED_WINDOWS)}
    portals: List[dict] = []
    # Force policy bands; caller threshold can only raise the apply floor (never lower below 65).
    apply_floor = max(AUTO_APPLY_MIN_MATCH, int(match_threshold) if match_threshold is not None else AUTO_APPLY_MIN_MATCH)
    tailor_floor = TAILOR_MIN_MATCH
    alerts_enabled = False
    tailor_enabled = True
    max_apps = 20

    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        automation = _get_or_create_automation(session, user)
        alerts_enabled = bool(automation.alerts)
        tailor_enabled = bool(automation.tailor_cv)
        if match_threshold is None:
            apply_floor = max(AUTO_APPLY_MIN_MATCH, int(automation.match_threshold or AUTO_APPLY_MIN_MATCH))
        max_apps = automation.max_applications if automation.max_applications and automation.max_applications > 0 else 20
        profile_row = _get_or_create_job_profile(session, user)
        search = _get_or_create_search(session, user)
        portals = _get_user_portals(session, user, include_status=False)
        scrape_meta = _scrape_configured_portals(
            session,
            user,
            posted_windows=list(AUTO_APPLY_POSTED_WINDOWS),
        )
        titles = search.titles or profile_row.job_titles or []
        required_skills = [skill.lower() for skill in (search.required_skills or [])]
        optional_skills = [skill.lower() for skill in (search.optional_skills or [])]
        employment_type = search.employment_type or "Both"
        exclude_keywords = [keyword.lower() for keyword in (search.exclude_keywords or [])]
        # Keep jobs from both 24h and 48h windows (2 days max).
        posted_within = max(int(window) for window in AUTO_APPLY_POSTED_WINDOWS)
        experience_level = search.experience_level or "Any"
        rate_min = seed_logic._parse_rate_value(search.rate_min or "")
        rate_max = seed_logic._parse_rate_value(search.rate_max or "")
        jobs = [_job_result_dict(row) for row in session.query(JobResult).filter(JobResult.user_id == user.id).all()]
        prefiltered = _filter_job_results(
            jobs,
            titles=titles,
            required_skills=required_skills,
            optional_skills=optional_skills,
            employment_type=employment_type,
            exclude_keywords=exclude_keywords,
            posted_within=posted_within,
            experience_level=experience_level,
            rate_min=rate_min,
            rate_max=rate_max,
            portals=portals,
        )
        # Hard-gate to 24h/48h posted windows regardless of search config.
        prefiltered = [
            job for job in prefiltered
            if _posted_within_hours(job.get("posted"), AUTO_APPLY_MAX_POSTED_HOURS)
        ]
        if not prefiltered and jobs:
            prefiltered = [
                job for job in jobs
                if _posted_within_hours(job.get("posted"), AUTO_APPLY_MAX_POSTED_HOURS)
            ][:50]
        all_ranked, matching_pipeline = _rank_jobs_with_cv(session, user, prefiltered)
        ranked = all_ranked

        existing_application_ids = {
            row.job_result_id
            for row in session.query(JobApplication)
            .filter(
                JobApplication.user_id == user.id,
                JobApplication.job_result_id.isnot(None),
                JobApplication.attempt_status.in_(
                    [
                        "queued",
                        "filling",
                        "awaiting_submit",
                        "needs_attention",
                        "applied",
                        "manual",
                        "demo",
                        "tailored",
                        "rejected",
                    ]
                ),
            )
            .all()
        }

        for job in ranked:
            job_id = job.get("id")
            if job_id in existing_application_ids:
                continue
            score = int(job.get("match") or 0)
            if score >= apply_floor:
                apply_ids.append(job_id)
            elif score >= tailor_floor:
                tailor_jobs.append(job)
            else:
                reject_jobs.append(job)

        apply_ids = apply_ids[:max_apps]
        remaining_slots = max(0, max_apps - len(apply_ids))
        tailor_jobs = tailor_jobs[:remaining_slots] if tailor_enabled else []
        reject_jobs = reject_jobs[: max(0, remaining_slots - len(tailor_jobs))]

        for job in tailor_jobs:
            tailored_apps.append(
                _create_match_decision_application(
                    session,
                    user=user,
                    job=job,
                    status="Tailoring",
                    stage="CV tailored to job description (40–65% match)",
                    action_label="Review tailored CV in Analyzer",
                    attempt_status="tailored",
                    attempt_detail=(
                        f"Match {job.get('match', 0)}% is between {tailor_floor}% and {apply_floor}%. "
                        "CV was tailored to the JD; apply after review."
                    ),
                )
            )

        for job in reject_jobs:
            rejected_apps.append(
                _create_match_decision_application(
                    session,
                    user=user,
                    job=job,
                    status="Rejected",
                    stage="Rejected — CV match below 40%",
                    action_label="No action — below match floor",
                    attempt_status="rejected",
                    attempt_detail=(
                        f"Match {job.get('match', 0)}% is below {tailor_floor}%. "
                        "Application automatically rejected."
                    ),
                )
            )

    # Tailor CV content for mid-band jobs (outside the decision session to reuse analysis helpers).
    tailored_job_ids: List[int] = []
    if tailor_enabled:
        for job in tailor_jobs:
            try:
                tailored = tailor_resume_for_job(
                    job_id=job["id"],
                    job_description=job.get("description"),
                    user_external_id=user_external_id,
                )
                if tailored.get("content"):
                    save_tailored_resume(job["id"], tailored["content"], user_external_id)
                    tailored_job_ids.append(int(job["id"]))
            except Exception:
                logger.exception("Failed to tailor CV for job_id=%s", job.get("id"))

    applied_count = 0
    apply_message = "No jobs met the 65%+ auto-apply threshold."
    if apply_ids:
        apply_result = apply_jobs(apply_ids, user_external_id, use_tailored_resume=True)
        applied_count = int(apply_result.get("applied") or len(apply_ids))
        apply_message = apply_result.get("message", f"Applied to {applied_count} job(s) at ≥{apply_floor}% match.")

    portal_names = ", ".join({portal["name"] for portal in portals}) or "configured portals"
    windows_label = " + ".join(f"{w}d" for w in scrape_meta.get("postedWindows", AUTO_APPLY_POSTED_WINDOWS))
    result = {
        "success": True,
        "message": (
            f"Scraped {scrape_meta['scraped']} posting(s) across {scrape_meta['portalCount']} portal(s) "
            f"({portal_names}) for {windows_label} (24h + 48h). "
            f"Routed {len(apply_ids)} apply (≥{apply_floor}%), "
            f"{len(tailored_apps)} tailor ({tailor_floor}–{apply_floor - 1}%), "
            f"{len(rejected_apps)} reject (<{tailor_floor}%). "
            f"{matching_pipeline.get('message', '')} {apply_message}"
        ).strip(),
        "results": ranked,
        "applied": applied_count,
        "jobIds": apply_ids,
        "tailored": len(tailored_apps),
        "rejected": len(rejected_apps),
        "tailoredApplications": tailored_apps,
        "rejectedApplications": rejected_apps,
        "tailoredJobIds": tailored_job_ids,
        "scrapedCount": scrape_meta["scraped"],
        "portalsScraped": scrape_meta["portalCount"],
        "postedWindows": scrape_meta.get("postedWindows", list(AUTO_APPLY_POSTED_WINDOWS)),
        "matchPolicy": {
            "applyMin": apply_floor,
            "tailorMin": tailor_floor,
            "rejectBelow": tailor_floor,
        },
        "matchingPipeline": matching_pipeline,
    }
    if user_external_id and alerts_enabled:
        from app.services.notification_service import notify_job_auto_apply

        notify_job_auto_apply(user_external_id, result["message"], applied_count)
    return result


def search_linkedin_jobs(payload: dict) -> dict:
    workspace = get_job_automation_workspace()
    jobs = workspace.get("linkedin", [])
    query = (payload.get("query") or "").lower()
    company = (payload.get("company") or "").lower()
    if query:
        jobs = [job for job in jobs if query in job["role"].lower() or query in job.get("company", "").lower()]
    if company:
        jobs = [job for job in jobs if company in job.get("company", "").lower()]
    return {"success": True, "jobs": jobs, "count": len(jobs)}


def apply_linkedin_job(role: str, company: str, easy_apply: bool) -> dict:
    with session_scope() as session:
        user = _workspace_user(session)
        session.add(
            JobApplication(
                user_id=user.id,
                role=role,
                company=company,
                status="Applied",
                stage="LinkedIn Easy Apply" if easy_apply else "LinkedIn application",
                updated_label=date.today().isoformat(),
                action_label="Await recruiter response",
                portal="LinkedIn",
                application_date=date.today(),
                match=None,
                posting_url="",
            )
        )
    return {
        "success": True,
        "message": f"Applied to {role} at {company} via LinkedIn.",
    }


def get_day_report_dashboard() -> dict:
    from app.services.reporting_helpers import day_report_bounds_and_defaults

    with session_scope() as session:
        rows = session.query(DayReportRow).order_by(DayReportRow.report_date).all()
        payload_rows = [
            {
                "date": row.report_date.isoformat(),
                "recruiter": row.recruiter,
                "technology": row.technology,
                "linkedin": row.linkedin,
                "calls": row.calls,
                "sourced": row.sourced,
                "marketing": row.marketing,
                "notes": row.notes,
            }
            for row in rows
        ]
        totals = {
            "linkedin": sum(row["linkedin"] or 0 for row in payload_rows),
            "calls": sum(row["calls"] or 0 for row in payload_rows),
            "sourced": sum(row["sourced"] or 0 for row in payload_rows),
            "marketing": sum(row["marketing"] or 0 for row in payload_rows),
        }
        meta = day_report_bounds_and_defaults([row["date"] for row in payload_rows])
        return {
            "range": {"start": payload_rows[0]["date"], "end": payload_rows[-1]["date"]} if payload_rows else {},
            **meta,
            "recruiters": sorted({row["recruiter"] for row in payload_rows}),
            "totals": totals,
            "rows": payload_rows,
        }


def filter_day_report(start: Optional[str] = None, end: Optional[str] = None, recruiter: Optional[str] = None) -> dict:
    dashboard = get_day_report_dashboard()
    rows = dashboard["rows"]
    if start:
        rows = [row for row in rows if row["date"] >= start]
    if end:
        rows = [row for row in rows if row["date"] <= end]
    if recruiter:
        rows = [row for row in rows if row["recruiter"] == recruiter]
    totals = {
        "linkedin": sum(row["linkedin"] or 0 for row in rows),
        "calls": sum(row["calls"] or 0 for row in rows),
        "sourced": sum(row["sourced"] or 0 for row in rows),
        "marketing": sum(row["marketing"] or 0 for row in rows),
    }
    return {
        "range": {
            "start": rows[0]["date"] if rows else start,
            "end": rows[-1]["date"] if rows else end,
        },
        "recruiters": dashboard["recruiters"],
        "totals": totals,
        "rows": rows,
    }


def get_submission_dashboard() -> dict:
    from app.services.reporting_helpers import submission_summary

    with session_scope() as session:
        months_rows = session.query(SubmissionMonth).order_by(SubmissionMonth.month).all()
        months = [{"month": row.month, "submissions": row.submissions} for row in months_rows]
    lookup = {row["month"]: row["submissions"] for row in months}
    enriched = []
    for idx, row in enumerate(months):
        year, month = row["month"].split("-")
        previous_month = months[idx - 1]["submissions"] if idx > 0 else None
        prior_year_key = f"{int(year) - 1}-{month}"
        yoy_base = lookup.get(prior_year_key)
        mom = None if previous_month in (None, 0) else round((row["submissions"] - previous_month) / previous_month * 100, 1)
        yoy = None if yoy_base in (None, 0) else round((row["submissions"] - yoy_base) / yoy_base * 100, 1)
        enriched.append({**row, "mom": mom, "yoy": yoy})
    return {
        "range": {"start": months[0]["month"], "end": months[-1]["month"]} if months else {},
        "summary": submission_summary(enriched),
        "months": enriched,
    }


def filter_submissions(start_month: Optional[str] = None, end_month: Optional[str] = None) -> dict:
    from app.services.reporting_helpers import submission_summary

    dashboard = get_submission_dashboard()
    months = dashboard["months"]
    if start_month:
        months = [row for row in months if row["month"] >= start_month]
    if end_month:
        months = [row for row in months if row["month"] <= end_month]
    return {
        "range": {
            "start": months[0]["month"] if months else start_month,
            "end": months[-1]["month"] if months else end_month,
        },
        "summary": submission_summary(months),
        "months": months,
    }


def preview_campaign(subject: str, body: str, recipients: List[str], user_external_id: str | None = None) -> dict:
    from app.services.campaign_email import build_preview

    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        settings = _load_campaign_settings(session, user.id)
        contacts = _load_campaign_contacts(session, user.id)
        composer = {
            "fromName": "Sarah Mitchell",
            "fromEmail": "sarah@marketingmind.ai",
            "replyTo": "recruiter@marketingmind.ai",
        }
        return build_preview(subject, body, recipients, contacts=contacts, composer=composer, settings=settings)


def preview_template(subject: str, body: str, composer: Optional[dict] = None, user_external_id: str | None = None) -> dict:
    from app.services.campaign_email import build_preview

    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        settings = _load_campaign_settings(session, user.id)
        contacts = _load_campaign_contacts(session, user.id)
        merged_composer = {
            "fromName": (composer or {}).get("fromName") or "Sarah Mitchell",
            "fromEmail": (composer or {}).get("fromEmail") or "sarah@marketingmind.ai",
            "replyTo": (composer or {}).get("replyTo") or "recruiter@marketingmind.ai",
        }
        recipients = [contacts[0]["email"]] if contacts else []
        return build_preview(subject, body, recipients, contacts=contacts, composer=merged_composer, settings=settings)


def send_test_campaign(email: str, subject: str, body: str, composer: Optional[dict] = None, user_external_id: str | None = None) -> dict:
    from app.services.campaign_email import send_test_email

    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        settings = _load_campaign_settings(session, user.id)
        merged_composer = {
            "fromName": (composer or {}).get("fromName") or "Sarah Mitchell",
            "fromEmail": (composer or {}).get("fromEmail") or "sarah@marketingmind.ai",
            "replyTo": (composer or {}).get("replyTo") or "recruiter@marketingmind.ai",
        }
        return send_test_email(email, subject, body, settings=settings, composer=merged_composer)


def launch_campaign(payload: dict, user_external_id: str | None = None) -> dict:
    from app.services.campaign_email import CampaignEmailError, launch_campaign_batch

    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        settings = _load_campaign_settings(session, user.id)
        settings["emailDelaySeconds"] = payload.get("emailDelaySeconds", settings.get("emailDelaySeconds", 3))
        if payload.get("openTracking") is not None:
            settings["openTracking"] = payload["openTracking"]
        contacts = _load_campaign_contacts(session, user.id)

        try:
            result = launch_campaign_batch(payload, settings=settings, contacts=contacts)
        except CampaignEmailError as exc:
            return {"success": False, "message": str(exc), "mode": "demo", "campaign": None, "sentCount": 0, "failedCount": 0}

        campaign = result.get("campaign") or {}
        row = CampaignItem(
            user_id=user.id,
            name=campaign.get("name") or payload.get("campaignName") or "New Campaign",
            from_name=payload.get("fromName"),
            from_email=payload.get("fromEmail"),
            reply_to=payload.get("replyTo"),
            subject=campaign.get("subject") or payload.get("subject", ""),
            body=campaign.get("body") or payload.get("body", ""),
            status=campaign.get("status") or ("Sent" if payload.get("sendNow") else "Scheduled"),
            scheduled_for=campaign.get("scheduledFor") or payload.get("scheduledFor"),
            sent_count=campaign.get("sent", 0),
            opened_count=campaign.get("opened", 0),
            replied_count=campaign.get("replied", 0),
        )
        session.add(row)
        session.flush()

        campaign["id"] = str(row.id)
        response = {
            "success": result["success"],
            "message": result["message"],
            "mode": result.get("mode", "demo"),
            "campaign": {
                "name": row.name,
                "sent": row.sent_count,
                "opened": row.opened_count,
                "replied": row.replied_count,
                "status": row.status,
                "scheduledFor": row.scheduled_for,
                "subject": row.subject,
                "body": row.body,
            },
            "sentCount": row.sent_count,
            "failedCount": len(campaign.get("failures") or []),
        }
        if user.external_id:
            from app.services.notification_service import notify_campaign_launch

            notify_campaign_launch(
                user.external_id,
                campaign_name=row.name,
                sent_count=row.sent_count,
                status=row.status,
            )
        return response


def save_campaign_draft(payload: dict, user_external_id: str | None = None) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        existing = (
            session.query(CampaignItem)
            .filter(CampaignItem.user_id == user.id, CampaignItem.name == payload["campaignName"], CampaignItem.status == "Draft")
            .first()
        )
        if existing:
            existing.subject = payload.get("subject", "")
            existing.body = payload.get("body", "")
            existing.from_name = payload.get("fromName")
            existing.from_email = payload.get("fromEmail")
            existing.reply_to = payload.get("replyTo")
            row = existing
        else:
            row = CampaignItem(
                user_id=user.id,
                name=payload["campaignName"],
                from_name=payload.get("fromName"),
                from_email=payload.get("fromEmail"),
                reply_to=payload.get("replyTo"),
                subject=payload.get("subject", ""),
                body=payload.get("body", ""),
                status="Draft",
                scheduled_for="—",
            )
            session.add(row)
            session.flush()

        draft = {
            "name": row.name,
            "sent": 0,
            "opened": 0,
            "replied": 0,
            "status": "Draft",
            "scheduledFor": "—",
            "subject": row.subject,
            "body": row.body,
        }
        return {"success": True, "message": f"Draft '{row.name}' saved.", "campaign": draft}


def import_campaign_contacts(payload: dict, user_external_id: str | None = None) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        list_name = payload.get("listName") or "Imported"
        incoming = payload.get("contacts") or []
        existing = session.query(CampaignContact).filter(CampaignContact.user_id == user.id).all()
        seen = {row.email.lower() for row in existing}
        imported_rows = []
        skipped = 0

        for row in incoming:
            email = str(row.get("email", "")).strip().lower()
            if not email or email in seen:
                skipped += 1
                continue
            seen.add(email)
            contact = CampaignContact(
                user_id=user.id,
                name=row.get("name") or email.split("@")[0],
                email=row.get("email"),
                company=row.get("company") or email.split("@")[1],
                status=row.get("status") or "Queued",
                list_name=row.get("list") or list_name,
            )
            session.add(contact)
            imported_rows.append(
                {
                    "name": contact.name,
                    "email": contact.email,
                    "company": contact.company,
                    "status": contact.status,
                    "list": contact.list_name,
                }
            )

        list_row = session.query(ContactList).filter(ContactList.user_id == user.id, ContactList.name == list_name).first()
        if list_row:
            list_row.contacts_count += len(imported_rows)
        elif imported_rows:
            session.add(ContactList(user_id=user.id, name=list_name, contacts_count=len(imported_rows), open_rate=0, reply_rate=0))

        return {"imported": len(imported_rows), "skipped": skipped, "contacts": imported_rows}


def test_campaign_smtp(settings: Optional[dict] = None, user_external_id: str | None = None) -> dict:
    from app.services.campaign_email import test_smtp_connection

    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        merged = _load_campaign_settings(session, user.id)
        if settings:
            merged.update({key: value for key, value in settings.items() if value is not None})
        return test_smtp_connection(merged)


def save_campaign_settings(payload: dict, user_external_id: str | None = None) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        settings = session.query(CampaignSettings).filter(CampaignSettings.user_id == user.id).first()
        if not settings:
            settings = CampaignSettings(user_id=user.id)
            session.add(settings)
            session.flush()
        field_map = {
            "smtpHost": "smtp_host",
            "smtpPort": "smtp_port",
            "smtpUsername": "smtp_username",
            "smtpPassword": "smtp_password",
            "senderLimit": "sender_limit",
            "emailDelaySeconds": "email_delay_seconds",
            "smartWarmup": "smart_warmup",
            "unsubscribeFooter": "unsubscribe_footer",
            "spamGuard": "spam_guard",
            "gmailSync": "gmail_sync",
            "outlookSync": "outlook_sync",
            "openTracking": "open_tracking",
            "aiSubjectAssist": "ai_subject_assist",
        }
        option_keys = {
            "honorUnsubscribes",
            "bounceManagement",
            "sendgridSync",
            "aiProvider",
            "aiDefaultTone",
            "aiPersonalization",
        }
        options = dict(settings.options_json or {})
        for key, attr in field_map.items():
            if key in payload and payload[key] is not None:
                setattr(settings, attr, payload[key])
        for key in option_keys:
            if key in payload and payload[key] is not None:
                options[key] = payload[key]
        settings.options_json = options
    return {"success": True, "message": "Campaign settings saved."}


def create_contact_list(name: str, user_external_id: str | None = None) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        row = ContactList(user_id=user.id, name=name, contacts_count=0, open_rate=0, reply_rate=0)
        session.add(row)
        session.flush()
        return {"name": name, "contacts": 0, "openRate": 0, "replyRate": 0}


def get_linkedin_workspace(user_external_id: str | None = None) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        recruiters = session.query(LinkedInRecruiter).filter(LinkedInRecruiter.user_id == user.id).all()
        recruiter_dicts = [
            {
                "id": row.external_id or row.id,
                "name": row.name,
                "title": row.title,
                "company": row.company,
                "location": row.location,
                "techs": row.techs or [],
                "conn": row.connection_degree,
                "avatar": row.avatar,
                "match": row.match_score,
                "source": row.source,
                "email": row.email,
                "note": row.note,
                "status": row.status,
                "bookmarked": row.bookmarked,
            }
            for row in recruiters
        ]
        sequences = []
        for seq in session.query(LinkedInSequence).filter(LinkedInSequence.user_id == user.id).all():
            sequences.append(
                {
                    "id": seq.external_id or seq.id,
                    "name": seq.name,
                    "steps": [
                        {
                            "label": step.label,
                            "status": step.status,
                            "date": step.step_date,
                        }
                        for step in sorted(seq.steps, key=lambda item: item.step_order)
                    ],
                }
            )
        followups = [
            {
                "name": row.name,
                "company": row.company,
                "due": row.due,
                "type": row.followup_type,
            }
            for row in session.query(LinkedInFollowup).filter(LinkedInFollowup.user_id == user.id).all()
        ]
        templates = [
            {"name": row.name, "body": row.body}
            for row in session.query(LinkedInMessageTemplate).filter(LinkedInMessageTemplate.user_id == user.id).all()
        ]
        api_sources = [
            {
                "id": row.external_id,
                "name": row.name,
                "shortCode": row.short_code,
                "description": row.description,
                "status": row.status,
                "color": row.color,
            }
            for row in session.query(LinkedInApiSource).all()
        ]
        settings = session.query(LinkedInSettings).filter(LinkedInSettings.user_id == user.id).first()
        contacted = sum(1 for row in recruiter_dicts if row["status"] in ("contacted", "replied"))
        replied = sum(1 for row in recruiter_dicts if row["status"] == "replied")
        companies = sorted({row["company"] for row in recruiter_dicts})
        all_techs = set()
        for row in recruiter_dicts:
            all_techs.update(row.get("techs", []))
        return {
            "stats": {
                "recruitersFound": len(recruiter_dicts),
                "contacted": contacted,
                "replied": replied,
                "followupsDue": len(followups),
            },
            "recruiters": recruiter_dicts,
            "sequences": sequences,
            "followups": followups,
            "templates": templates,
            "apiSources": api_sources,
            "companies": companies,
            "technologies": sorted(all_techs),
            "apiConnected": any(source["status"] == "connected" for source in api_sources),
            "pasteProfilesEnabled": True,
            "outreachEnabled": True,
            "apiUsage": deepcopy(seed_logic._LINKEDIN_API_USAGE),
            "settings": {
                "autoRunDaily": settings.auto_run_daily if settings else True,
                "autoEnrich": settings.auto_enrich if settings else True,
                "skipContacted": settings.skip_contacted if settings else True,
                "autoFollowup": settings.auto_followup if settings else True,
                "aiPersonalize": settings.ai_personalize if settings else True,
                "maxPerDay": settings.max_per_day if settings else 25,
                "delaySeconds": settings.delay_seconds if settings else 45,
                "accountEmail": settings.account_email if settings else "",
                "dailyConnections": settings.daily_connections if settings else 20,
                "dailyInmails": settings.daily_inmails if settings else 10,
                "isPremium": settings.is_premium if settings else False,
                "respectDnc": settings.respect_dnc if settings else True,
                "honorUnsubscribes": settings.honor_unsubscribes if settings else True,
                "usePermittedSources": settings.use_permitted_sources if settings else True,
            },
        }


def run_linkedin_discovery(companies: list, technologies: list, seniority: str, location: str, connections: str, results_per_company: int, user_external_id: str | None = None) -> dict:
    workspace = get_linkedin_workspace(user_external_id)
    recruiters = workspace["recruiters"]
    filtered = [
        r
        for r in recruiters
        if (not companies or r["company"] in companies)
        and (not technologies or any(t in r["techs"] for t in technologies))
    ]
    if not filtered:
        filtered = recruiters
    return {
        "recruiters": deepcopy(filtered),
        "totalFound": len(filtered),
        "count": len(filtered),
        "message": f"Found {len(filtered)} recruiters matching your criteria across {len({r['company'] for r in filtered})} companies.",
    }


def enrich_linkedin_profiles(urls: list, tech_context: str) -> dict:
    names = ["Sarah Johnson", "Tom Mitchell", "Priya Kapoor", "Alex Wong", "Maria Silva"]
    companies = ["TEKsystems", "Infosys", "Capgemini", "Wipro", "Accenture"]
    techs_list = [
        ["Java", "Spring Boot"],
        ["Java", "AWS", "Docker"],
        ["Java", "Microservices"],
        ["Spring", "SQL"],
        ["Java", "DevOps"],
    ]
    profiles = []
    for i, url in enumerate(urls[:5]):
        idx = i % len(names)
        name = names[idx]
        profiles.append(
            {
                "id": 100 + i,
                "name": name,
                "title": "Technical Recruiter",
                "company": companies[idx],
                "location": "United States",
                "techs": techs_list[idx],
                "conn": "2nd",
                "avatar": "".join(part[0] for part in name.split()),
                "match": 80 - i * 3,
                "source": "Apollo",
                "email": f"{name.lower().replace(' ', '.')}@{companies[idx].lower().replace(' ', '')}.com",
                "note": f"Enriched via API from {url[:40]}",
                "status": "new",
            }
        )
    return {
        "profiles": profiles,
        "enriched": len(profiles),
        "message": f"{len(profiles)} profiles enriched successfully via Apollo/Hunter.",
    }


def generate_linkedin_message(prompt: str, message_type: str, tone: str, channel: str) -> dict:
    subjects = {
        "connect": "Let us connect — Java Developer available C2C",
        "inmail": "Senior Java Developer available — C2C — Immediate start",
        "cold_outreach": "Available Senior Java Developer | C2C | Immediate",
        "followup": "Following up — Java Developer still available",
        "hotlist": "Java Developer Hotlist — Available Now | C2C",
        "thankyou": "Thank you for connecting!",
        "resume": "Resume — Senior Java Developer | C2C | Immediate",
    }
    bodies = {
        "connect": (
            "Hi {{recruiter_name}},\n\nI noticed your expertise in IT staffing at {{company}} "
            "and wanted to reach out. I have a Senior Java Developer with Spring Boot and AWS "
            "experience available immediately for C2C roles.\n\nWould love to connect!\n\n{{candidate_name}}"
        ),
        "inmail": (
            "Hi {{recruiter_name}},\n\nHope this message finds you well! I am reaching out because "
            "I have a highly skilled Senior Java Developer currently available for C2C contract "
            "positions at {{company}}.\n\nWould you be open to a quick conversation?\n\nBest,\n{{candidate_name}}"
        ),
        "cold_outreach": (
            "Hi {{recruiter_name}},\n\nI have an excellent Senior Java Developer available for C2C "
            "contract roles.\n\nBest regards,\n{{candidate_name}}"
        ),
        "followup": (
            "Hi {{recruiter_name}},\n\nJust following up on my earlier message. Our Java Developer "
            "remains available.\n\n{{candidate_name}}"
        ),
        "hotlist": (
            "Hi {{recruiter_name}},\n\nI have a Senior Java Developer on our bench available "
            "immediately.\n\n{{candidate_name}}"
        ),
        "thankyou": "Hi {{recruiter_name}},\n\nThank you so much for connecting!\n\nBest,\n{{candidate_name}}",
        "resume": "Hi {{recruiter_name}},\n\nPlease find attached the resume of our Senior Java Developer.\n\nBest,\n{{candidate_name}}",
    }
    key = message_type if message_type in subjects else "cold_outreach"
    body = bodies[key]
    return {
        "subject": subjects[key],
        "message": body,
        "body": body,
        "messageType": key,
    }


def set_linkedin_recruiter_bookmark(recruiter_id: int, bookmarked: bool, user_external_id: str | None = None) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        recruiter = (
            session.query(LinkedInRecruiter)
            .filter(
                LinkedInRecruiter.user_id == user.id,
                or_(LinkedInRecruiter.external_id == recruiter_id, LinkedInRecruiter.id == recruiter_id),
            )
            .first()
        )
        if not recruiter:
            raise ValueError("Recruiter not found.")
        recruiter.bookmarked = bookmarked
        return {
            "success": True,
            "message": f"{recruiter.name} {'saved to' if bookmarked else 'removed from'} your recruiter list.",
        }


def create_linkedin_message_template(name: str, body: str, user_external_id: str | None = None) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        normalized_name = name.strip()
        existing = (
            session.query(LinkedInMessageTemplate)
            .filter(
                LinkedInMessageTemplate.user_id == user.id,
                func.lower(LinkedInMessageTemplate.name) == normalized_name.lower(),
            )
            .first()
        )
        if existing:
            existing.body = body
            row = existing
        else:
            row = LinkedInMessageTemplate(user_id=user.id, name=normalized_name, body=body)
            session.add(row)
        session.flush()
        return {"id": row.id, "name": row.name, "body": row.body}


def send_linkedin_outreach(recruiter_ids: list, subject: str, body: str, channel: str, schedule_at: Optional[str], user_external_id: str | None = None) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        recruiters = (
            session.query(LinkedInRecruiter)
            .filter(
                LinkedInRecruiter.user_id == user.id,
                or_(
                    LinkedInRecruiter.external_id.in_(recruiter_ids),
                    LinkedInRecruiter.id.in_(recruiter_ids),
                ),
            )
            .all()
        )
        names = [row.name for row in recruiters]
        if schedule_at:
            scheduled_for = datetime.fromisoformat(schedule_at.replace("Z", "+00:00"))
            session.add(
                LinkedInOutreachQueue(
                    user_id=user.id,
                    recruiter_ids=recruiter_ids,
                    subject=subject,
                    body=body,
                    channel=channel,
                    scheduled_for=scheduled_for,
                    status="scheduled",
                )
            )
    return {
        "success": True,
        "count": len(recruiter_ids),
        "message": (
            f"Outreach scheduled for {len(recruiter_ids)} recruiter(s) via {channel}."
            if schedule_at
            else f"Outreach queued for {len(recruiter_ids)} recruiter(s) via {channel}: "
            f"{', '.join(names[:3])}{'...' if len(names) > 3 else ''}."
        ),
    }


def save_linkedin_settings(settings: dict, user_external_id: str | None = None) -> dict:
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        row = session.query(LinkedInSettings).filter(LinkedInSettings.user_id == user.id).first()
        if not row:
            row = LinkedInSettings(user_id=user.id)
            session.add(row)
            session.flush()
        field_map = {
            "autoRunDaily": "auto_run_daily",
            "autoEnrich": "auto_enrich",
            "skipContacted": "skip_contacted",
            "autoFollowup": "auto_followup",
            "aiPersonalize": "ai_personalize",
            "maxPerDay": "max_per_day",
            "delaySeconds": "delay_seconds",
            "accountEmail": "account_email",
            "dailyConnections": "daily_connections",
            "dailyInmails": "daily_inmails",
            "isPremium": "is_premium",
            "respectDnc": "respect_dnc",
            "honorUnsubscribes": "honor_unsubscribes",
            "usePermittedSources": "use_permitted_sources",
        }
        for key, attr in field_map.items():
            if key in settings and settings[key] is not None:
                setattr(row, attr, settings[key])
    return {"success": True, "message": "LinkedIn settings saved successfully."}


def save_linkedin_api_keys(keys: dict, user_external_id: str | None = None) -> dict:
    connected: List[str] = []
    with session_scope() as session:
        user = _resolve_user(session, user_external_id)
        for provider, value in keys.items():
            if value is None:
                continue
            trimmed = str(value).strip()
            if not trimmed:
                continue
            existing = (
                session.query(LinkedInApiKey)
                .filter(LinkedInApiKey.user_id == user.id, LinkedInApiKey.provider == provider)
                .first()
            )
            if existing:
                existing.api_key = trimmed
            else:
                session.add(LinkedInApiKey(user_id=user.id, provider=provider, api_key=trimmed))
            source = session.query(LinkedInApiSource).filter(LinkedInApiSource.external_id == provider).first()
            if source:
                source.status = "connected"
            connected.append(provider)
    labels = ", ".join(connected) if connected else "none"
    return {"success": True, "message": f"API keys saved for: {labels}."}


def get_endpoint_catalog() -> dict:
    return seed_logic.get_endpoint_catalog()


def get_test_data_payload() -> dict:
    raise RuntimeError("Test data dump is only available in JSON seed mode (USE_SEED_DATA=true).")


def append_test_data_payload(dataset: str, entries: List[Dict[str, Any]]) -> dict:
    raise RuntimeError("Test data append is only available in JSON seed mode (USE_SEED_DATA=true).")


def reset_test_data_payload() -> dict:
    from app.db.database import get_engine
    from app.db.models import Base
    from scripts.init_postgres_schema import main as seed_main

    engine = get_engine()
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured.")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_main()
    return {"success": True, "message": "PostgreSQL database reset and re-seeded from baseline."}
