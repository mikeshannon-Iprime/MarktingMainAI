#!/usr/bin/env python3
"""
Initialize PostgreSQL schema and seed MarketingMind AI data.

Usage (from backend/):
    python scripts/init_postgres_schema.py

Connection defaults (override via env DATABASE_URL):
    postgresql+psycopg://postgres:admin@localhost:5432/postgres
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.passwords import hash_password
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db.database import _normalize_database_url
from app.db.models import (
    Base,
    CampaignContact,
    CampaignItem,
    CampaignSettings,
    CampaignTemplate,
    Carrier,
    ContactList,
    DayReportRow,
    JobApplication,
    JobAutomationSettings,
    JobProfile,
    JobResult,
    JobAnalysis,
    LinkedInApiSource,
    LinkedInFollowup,
    LinkedInJob,
    LinkedInMessageTemplate,
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
    UserSettings,
)

DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:admin@localhost:5432/postgres"

DEMO_USERS = [
    {
        "external_id": "u-super-1",
        "name": "Super Admin",
        "email": "superadmin@marketingmind.ai",
        "password_hash": "Super@123",
        "role": "super_admin",
        "phone": "+1-555-0102",
        "company": "MarketingMind",
        "title": "Chief Operations Officer",
        "department": "Executive",
        "location": "New York, NY",
        "timezone": "America/New_York",
        "bio": "Leading the MarketingMind platform and overseeing all operations.",
    },
    {
        "external_id": "u-admin-1",
        "name": "Admin User",
        "email": "admin@marketingmind.ai",
        "password_hash": "Admin@123",
        "role": "admin",
        "phone": "+1-555-0101",
        "company": "MarketingMind",
        "title": "Platform Administrator",
        "department": "Operations",
        "location": "San Francisco, CA",
        "timezone": "America/Los_Angeles",
        "bio": "Platform admin managing campaign operations and recruiter dashboards.",
    },
    {
        "external_id": "u-user-1",
        "name": "Read Only User",
        "email": "user@marketingmind.ai",
        "password_hash": "User@123",
        "role": "user",
        "phone": "+1-555-0103",
        "company": "MarketingMind",
        "title": "Campaign Analyst",
        "department": "Marketing",
        "location": "Austin, TX",
        "timezone": "America/Chicago",
        "bio": "Analyzing campaign performance and reporting insights.",
    },
]

LINKEDIN_RECRUITERS = [
    {"id": 1, "name": "Sarah Chen", "title": "Technical Recruiter", "company": "TechStaff Inc", "location": "Dallas, TX", "techs": ["Java", "Spring"], "conn": "2nd", "avatar": "SC", "match": 92, "source": "LinkedIn", "email": "sarah@techstaff.com", "note": "Active Java hiring", "status": "new"},
    {"id": 2, "name": "Michael Torres", "title": "Senior Talent Partner", "company": "CloudBridge", "location": "Austin, TX", "techs": ["AWS", "DevOps"], "conn": "3rd", "avatar": "MT", "match": 85, "source": "Hunter", "email": "m.torres@cloudbridge.com", "note": "Cloud roles", "status": "contacted"},
]

LINKEDIN_SEQUENCES = [
    {"id": 1, "name": "Initial Outreach", "steps": [{"label": "Connection Request", "status": "done", "date": "Jun 10"}, {"label": "Follow-up Message", "status": "pending", "date": "Jun 14"}]},
]

LINKEDIN_FOLLOWUPS = [
    {"name": "Sarah Chen", "company": "TechStaff Inc", "due": "Today", "type": "LinkedIn message"},
]

LINKEDIN_TEMPLATES = [
    {"name": "Cold Intro", "body": "Hi {{name}}, I noticed your work at {{company}}..."},
]

LINKEDIN_API_SOURCES = [
    {"id": "apollo", "name": "Apollo.io", "shortCode": "AP", "description": "B2B contact database", "status": "connected", "color": "#6366f1"},
    {"id": "hunter", "name": "Hunter.io", "shortCode": "HU", "description": "Email finder", "status": "connected", "color": "#f59e0b"},
]

LINKEDIN_SETTINGS = {
    "autoRunDaily": True,
    "autoEnrich": True,
    "skipContacted": True,
    "autoFollowup": True,
    "aiPersonalize": True,
    "maxPerDay": 50,
    "delaySeconds": 30,
    "accountEmail": "recruiter@marketingmind.ai",
    "dailyConnections": 25,
    "dailyInmails": 10,
    "isPremium": True,
    "respectDnc": True,
    "honorUnsubscribes": True,
    "usePermittedSources": True,
}


def load_test_data() -> dict:
    path = BACKEND_ROOT / "app" / "data" / "test_data.json"
    return json.loads(path.read_text(encoding="utf-8"))


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def get_or_create_admin(session: Session) -> User:
    admin = session.query(User).filter(User.email == "admin@marketingmind.ai").first()
    if admin:
        return admin
    for row in DEMO_USERS:
        payload = dict(row)
        payload["password_hash"] = hash_password(payload["password_hash"])
        session.add(User(**payload))
    session.flush()
    admin = session.query(User).filter(User.email == "admin@marketingmind.ai").one()
    for user in session.query(User).all():
        if not user.settings:
            session.add(UserSettings(user_id=user.id))
    session.flush()
    return admin


def seed_users(session: Session) -> User:
    if session.query(User).count() > 0:
        return session.query(User).filter(User.email == "admin@marketingmind.ai").one()
    return get_or_create_admin(session)


def seed_campaigns(session: Session, data: dict, admin: User) -> None:
    if session.query(CampaignContact).count():
        return
    for row in data.get("campaign_contacts", []):
        session.add(
            CampaignContact(
                user_id=admin.id,
                name=row["name"],
                email=row["email"],
                company=row["company"],
                status=row.get("status", "Queued"),
                list_name=row.get("list", "Default"),
            )
        )
    for row in data.get("campaign_lists", []):
        session.add(
            ContactList(
                user_id=admin.id,
                name=row["name"],
                contacts_count=row.get("contacts", 0),
                open_rate=row.get("openRate", 0),
                reply_rate=row.get("replyRate", 0),
            )
        )
    for row in data.get("campaign_templates", []):
        session.add(
            CampaignTemplate(
                user_id=admin.id,
                name=row["name"],
                category=row.get("category", "General"),
                description=row.get("description"),
                subject=row.get("subject", row["name"]),
                body=row.get("body", ""),
            )
        )
    for row in data.get("campaign_items", []):
        session.add(
            CampaignItem(
                user_id=admin.id,
                name=row["name"],
                subject=row["name"],
                body="",
                status=row.get("status", "Draft"),
                scheduled_for=row.get("scheduledFor"),
                sent_count=row.get("sent", 0),
                opened_count=row.get("opened", 0),
                replied_count=row.get("replied", 0),
            )
        )
    settings = data.get("campaign_settings", {})
    if settings and not session.query(CampaignSettings).filter(CampaignSettings.user_id == admin.id).first():
        session.add(
            CampaignSettings(
                user_id=admin.id,
                smtp_host=settings.get("smtpHost", "smtp.gmail.com"),
                smtp_port=settings.get("smtpPort", 587),
                sender_limit=settings.get("senderLimit", 500),
                smart_warmup=settings.get("smartWarmup", True),
                unsubscribe_footer=settings.get("unsubscribeFooter", True),
                spam_guard=settings.get("spamGuard", True),
                gmail_sync=settings.get("gmailSync", False),
                outlook_sync=settings.get("outlookSync", False),
                open_tracking=settings.get("openTracking", True),
                ai_subject_assist=settings.get("aiSubjectAssist", True),
            )
        )


def seed_job_automation(session: Session, data: dict, admin: User) -> None:
    if session.query(JobProfile).filter(JobProfile.user_id == admin.id).first():
        return

    profile = data.get("job_profile", {})
    session.add(
        JobProfile(
            user_id=admin.id,
            name=profile.get("name", "John Smith"),
            email=profile.get("email", "john.smith@email.com"),
            phone=profile.get("phone", "+1 (555) 555-0128"),
            location=profile.get("location", "Dallas, TX"),
            linkedin=profile.get("linkedin", "https://linkedin.com/in/johnsmith"),
            experience=profile.get("experience", "5-8 Years"),
            employment_type=profile.get("employmentType", "Both Contract & Full Time"),
            rate=profile.get("rate", "$85/hr"),
            visa=profile.get("visa", "H1B"),
            work_mode=profile.get("workMode", "Hybrid"),
            job_titles=profile.get("jobTitles", []),
            resume_file_name=profile.get("resumeFileName"),
            resume_summary=profile.get("resumeSummary"),
            resume_skills=profile.get("resumeSkills", []),
        )
    )

    automation = data.get("job_automation", {})
    session.add(
        JobAutomationSettings(
            user_id=admin.id,
            auto_apply=automation.get("autoApply", False),
            match_threshold=automation.get("matchThreshold", 75),
            max_applications=automation.get("maxApplications", 20),
            alerts=automation.get("alerts", True),
            tailor_cv=automation.get("tailorCv", True),
            schedule_enabled=automation.get("scheduleEnabled", False),
            schedule_label=automation.get("scheduleLabel", ""),
            schedule_timezone=automation.get("scheduleTimezone", "America/New_York"),
            schedule_time=automation.get("scheduleTime", "09:00"),
        )
    )

    search = data.get("search_config", {})
    session.add(
        SearchConfig(
            user_id=admin.id,
            titles=search.get("titles", []),
            required_skills=search.get("requiredSkills", []),
            optional_skills=search.get("optionalSkills", []),
            location=search.get("location", ""),
            radius=search.get("radius", "50 miles"),
            filters=search.get("filters", []),
            exclude_keywords=search.get("excludeKeywords", []),
            employment_type=search.get("employmentType", "Both"),
            min_match_score=search.get("minMatchScore", 70),
            posted_within=search.get("postedWithin", "7"),
            experience_level=search.get("experienceLevel", "Any"),
            rate_min=search.get("rateMin", ""),
            rate_max=search.get("rateMax", ""),
            repeat_every=search.get("repeatEvery", "Once daily"),
        )
    )

    for row in data.get("portal_items", []):
        session.add(Portal(user_id=admin.id, name=row["name"], url=row["url"], status=row.get("status", "Active")))
    for row in data.get("carrier_items", []):
        session.add(Carrier(user_id=admin.id, name=row["name"], url=row["url"], status=row.get("status", "Monitoring")))

    for row in data.get("job_results", []):
        session.add(
            JobResult(
                id=row["id"],
                user_id=admin.id,
                role=row["role"],
                company=row["company"],
                location=row["location"],
                type=row["type"],
                posted=str(row["posted"]),
                rate=row.get("rate"),
                match=row.get("match", 0),
                hot=row.get("hot", False),
                skills=row.get("skills", []),
                portal_name=row.get("portalName"),
                portal_url=row.get("portalUrl"),
                source_url=row.get("sourceUrl"),
                description=row.get("description"),
            )
        )
    session.flush()

    for job_id in data.get("saved_jobs", []):
        session.add(SavedJob(user_id=admin.id, job_result_id=job_id))

    for row in data.get("applications", []):
        session.add(
            JobApplication(
                user_id=admin.id,
                role=row["role"],
                company=row["company"],
                status=row["status"],
                stage=row["stage"],
                updated_label=row.get("updated", ""),
                action_label=row.get("action", ""),
                portal=row.get("portal"),
                application_date=parse_date(row.get("date") or row.get("updated")),
                match=row.get("match"),
                posting_url=row.get("postingUrl"),
            )
        )

    tailored = data.get("tailored_resumes", {})
    for key, row in tailored.items():
        session.add(
            TailoredResume(
                user_id=admin.id,
                job_result_id=int(row.get("jobId", key)),
                content=row.get("content", ""),
            )
        )

    for row in data.get("linkedin_jobs", []):
        session.add(
            LinkedInJob(
                user_id=admin.id,
                role=row["role"],
                company=row["company"],
                location=row["location"],
                type=row.get("type"),
                posted=row.get("posted"),
                match=row.get("match"),
                easy_apply=row.get("easyApply", False),
                applicants=row.get("applicants", 0),
                insight=row.get("insight"),
                linkedin_url=row.get("linkedinUrl"),
                experience_level=row.get("experienceLevel"),
                date_posted=row.get("datePosted"),
            )
        )

    session.add(
        JobAnalysis(
            user_id=admin.id,
            job_result_id=1,
            score=87,
            summary="Strong fit for backend and cloud-heavy roles.",
            hits=["Java", "Spring Boot", "AWS"],
            misses=["Kubernetes", "GraphQL"],
            suggestions=["Highlight AWS migration outcomes."],
            skill_gaps=["Kubernetes"],
            recommendations=["Add Kubernetes to skills section."],
            experience_match="5-8 years aligns with senior roles.",
            title_match="Senior Java Developer matches target titles.",
        )
    )


def seed_linkedin(session: Session, admin: User) -> None:
    if session.query(LinkedInRecruiter).count():
        return
    for row in LINKEDIN_RECRUITERS:
        session.add(
            LinkedInRecruiter(
                user_id=admin.id,
                external_id=row.get("id"),
                name=row["name"],
                title=row["title"],
                company=row["company"],
                location=row["location"],
                techs=row.get("techs", []),
                connection_degree=row.get("conn", "2nd"),
                avatar=row.get("avatar"),
                match_score=row.get("match", 0),
                source=row.get("source", "LinkedIn"),
                email=row.get("email"),
                note=row.get("note"),
                status=row.get("status", "new"),
            )
        )
    session.flush()
    for seq in LINKEDIN_SEQUENCES:
        sequence = LinkedInSequence(user_id=admin.id, external_id=seq.get("id"), name=seq["name"])
        session.add(sequence)
        session.flush()
        for index, step in enumerate(seq.get("steps", [])):
            session.add(
                LinkedInSequenceStep(
                    sequence_id=sequence.id,
                    step_order=index,
                    label=step.get("label", ""),
                    status=step.get("status", "pending"),
                    step_date=step.get("date"),
                )
            )
    for row in LINKEDIN_FOLLOWUPS:
        session.add(
            LinkedInFollowup(
                user_id=admin.id,
                name=row["name"],
                company=row["company"],
                due=row["due"],
                followup_type=row["type"],
            )
        )
    for row in LINKEDIN_TEMPLATES:
        session.add(LinkedInMessageTemplate(user_id=admin.id, name=row["name"], body=row["body"]))
    for row in LINKEDIN_API_SOURCES:
        session.add(
            LinkedInApiSource(
                external_id=row.get("id"),
                name=row["name"],
                short_code=row["shortCode"],
                description=row["description"],
                status=row.get("status", "disconnected"),
                color=row.get("color", "#6b7280"),
            )
        )
    if not session.query(LinkedInSettings).filter(LinkedInSettings.user_id == admin.id).first():
        session.add(
            LinkedInSettings(
                user_id=admin.id,
                auto_run_daily=LINKEDIN_SETTINGS["autoRunDaily"],
                auto_enrich=LINKEDIN_SETTINGS["autoEnrich"],
                skip_contacted=LINKEDIN_SETTINGS["skipContacted"],
                auto_followup=LINKEDIN_SETTINGS["autoFollowup"],
                ai_personalize=LINKEDIN_SETTINGS["aiPersonalize"],
                max_per_day=LINKEDIN_SETTINGS["maxPerDay"],
                delay_seconds=LINKEDIN_SETTINGS["delaySeconds"],
                account_email=LINKEDIN_SETTINGS["accountEmail"],
                daily_connections=LINKEDIN_SETTINGS["dailyConnections"],
                daily_inmails=LINKEDIN_SETTINGS["dailyInmails"],
                is_premium=LINKEDIN_SETTINGS["isPremium"],
                respect_dnc=LINKEDIN_SETTINGS["respectDnc"],
                honor_unsubscribes=LINKEDIN_SETTINGS["honorUnsubscribes"],
                use_permitted_sources=LINKEDIN_SETTINGS["usePermittedSources"],
            )
        )


def seed_reporting(session: Session, data: dict) -> None:
    if session.query(DayReportRow).count():
        return
    for row in data.get("day_report_rows", []):
        session.add(
            DayReportRow(
                report_date=date.fromisoformat(row["date"]),
                recruiter=row["recruiter"],
                technology=row["technology"],
                linkedin=row.get("linkedin", 0),
                calls=row.get("calls", 0),
                sourced=row.get("sourced", 0),
                marketing=row.get("marketing", 0),
                notes=row.get("notes", ""),
            )
        )
    for row in data.get("submission_months", []):
        session.add(
            SubmissionMonth(
                month=row["month"],
                submissions=row.get("submissions", 0),
            )
        )


def create_schema(engine) -> list[str]:
    Base.metadata.create_all(bind=engine)
    return sorted(Base.metadata.tables.keys())


def main() -> int:
    database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    url = _normalize_database_url(database_url)
    print(f"Connecting to {url.split('@')[-1]} ...")

    engine = create_engine(url, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("Connection OK.")

    tables = create_schema(engine)
    print(f"Created/verified {len(tables)} tables:")
    for name in tables:
        print(f"  - {name}")

    data = load_test_data()
    with Session(engine) as session:
        admin = seed_users(session)
        seed_campaigns(session, data, admin)
        seed_job_automation(session, data, admin)
        seed_linkedin(session, admin)
        seed_reporting(session, data)
        session.commit()
    print("Seed data loaded successfully.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
