"""
PostgreSQL / SQLAlchemy data models for MarketingMind AI.

All application domains: auth, campaigns, job automation, LinkedIn, reporting.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ─── Auth & users ───────────────────────────────────────────────────────────


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    phone: Mapped[Optional[str]] = mapped_column(String(40))
    company: Mapped[Optional[str]] = mapped_column(String(120))
    title: Mapped[Optional[str]] = mapped_column(String(120))
    department: Mapped[Optional[str]] = mapped_column(String(120))
    location: Mapped[Optional[str]] = mapped_column(String(120))
    timezone: Mapped[Optional[str]] = mapped_column(String(64))
    bio: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    settings: Mapped[Optional["UserSettings"]] = relationship(back_populates="user", uselist=False)
    job_profile: Mapped[Optional["JobProfile"]] = relationship(back_populates="user", uselist=False)


class UserSettings(Base, TimestampMixin):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    campaign_alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    job_alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    daily_report: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    weekly_digest: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sms_notifications: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sms_phone: Mapped[Optional[str]] = mapped_column(String(40))
    language: Mapped[str] = mapped_column(String(16), default="en", nullable=False)
    date_format: Mapped[str] = mapped_column(String(32), default="MM/DD/YYYY", nullable=False)
    theme: Mapped[str] = mapped_column(String(16), default="light", nullable=False)

    user: Mapped["User"] = relationship(back_populates="settings")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


# ─── Campaigns ──────────────────────────────────────────────────────────────


class CampaignSettings(Base, TimestampMixin):
    __tablename__ = "campaign_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    smtp_host: Mapped[str] = mapped_column(String(255), default="smtp.gmail.com", nullable=False)
    smtp_port: Mapped[int] = mapped_column(Integer, default=587, nullable=False)
    sender_limit: Mapped[int] = mapped_column(Integer, default=500, nullable=False)
    smart_warmup: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    unsubscribe_footer: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    spam_guard: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    gmail_sync: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    outlook_sync: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    open_tracking: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ai_subject_assist: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    smtp_username: Mapped[Optional[str]] = mapped_column(String(255))
    smtp_password: Mapped[Optional[str]] = mapped_column(String(255))
    email_delay_seconds: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    options_json: Mapped[dict[Any, Any]] = mapped_column(JSONB, default=dict, nullable=False)


class ContactList(Base, TimestampMixin):
    __tablename__ = "contact_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    contacts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    open_rate: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reply_rate: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class CampaignContact(Base, TimestampMixin):
    __tablename__ = "campaign_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="Queued", nullable=False)
    list_name: Mapped[str] = mapped_column(String(120), default="Default", nullable=False)


class CampaignTemplate(Base, TimestampMixin):
    __tablename__ = "campaign_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="General", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)


class CampaignItem(Base, TimestampMixin):
    __tablename__ = "campaign_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    from_name: Mapped[Optional[str]] = mapped_column(String(120))
    from_email: Mapped[Optional[str]] = mapped_column(String(255))
    reply_to: Mapped[Optional[str]] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="Draft", nullable=False)
    scheduled_for: Mapped[Optional[str]] = mapped_column(String(64))
    sent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    opened_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    replied_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


# ─── Job automation ─────────────────────────────────────────────────────────


class JobProfile(Base, TimestampMixin):
    __tablename__ = "job_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(40), nullable=False)
    location: Mapped[str] = mapped_column(String(120), nullable=False)
    linkedin: Mapped[str] = mapped_column(String(255), nullable=False)
    experience: Mapped[str] = mapped_column(String(60), nullable=False)
    employment_type: Mapped[str] = mapped_column(String(80), nullable=False)
    rate: Mapped[str] = mapped_column(String(60), nullable=False)
    visa: Mapped[str] = mapped_column(String(40), nullable=False)
    work_mode: Mapped[str] = mapped_column(String(60), nullable=False)
    job_titles: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    resume_file_name: Mapped[Optional[str]] = mapped_column(String(255))
    resume_summary: Mapped[Optional[str]] = mapped_column(Text)
    resume_skills: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)

    user: Mapped["User"] = relationship(back_populates="job_profile")


class UserResume(Base, TimestampMixin):
    """One uploaded CV per row — users can hold multiple parsed resumes."""

    __tablename__ = "user_resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String(120))
    file_bytes: Mapped[Optional[bytes]] = mapped_column(LargeBinary)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    skills: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    job_titles: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    ml_score: Mapped[Optional[int]] = mapped_column(Integer)
    matched_skills: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    missing_skills: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Isolated contact + prefs + resume fields for this CV only (camelCase keys).
    profile_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "file_name", name="uq_user_resumes_user_file"),)


class JobAutomationSettings(Base, TimestampMixin):
    __tablename__ = "job_automation_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    auto_apply: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    match_threshold: Mapped[int] = mapped_column(Integer, default=65, nullable=False)
    max_applications: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tailor_cv: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    schedule_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    schedule_label: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    schedule_timezone: Mapped[str] = mapped_column(String(64), default="America/New_York", nullable=False)
    schedule_time: Mapped[str] = mapped_column(String(8), default="09:00", nullable=False)


class SearchConfig(Base, TimestampMixin):
    __tablename__ = "search_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    titles: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    required_skills: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    optional_skills: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    location: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    radius: Mapped[str] = mapped_column(String(32), default="50 miles", nullable=False)
    filters: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    exclude_keywords: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    employment_type: Mapped[str] = mapped_column(String(80), default="Both", nullable=False)
    min_match_score: Mapped[int] = mapped_column(Integer, default=70, nullable=False)
    posted_within: Mapped[str] = mapped_column(String(8), default="7", nullable=False)
    experience_level: Mapped[str] = mapped_column(String(64), default="Any", nullable=False)
    rate_min: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    rate_max: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    repeat_every: Mapped[str] = mapped_column(String(32), default="Once daily", nullable=False)


class Portal(Base, TimestampMixin):
    __tablename__ = "portals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="Active", nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "url", name="uq_portals_user_url"),)


class Carrier(Base, TimestampMixin):
    __tablename__ = "carriers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="Monitoring", nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "url", name="uq_carriers_user_url"),)


class JobResult(Base, TimestampMixin):
    __tablename__ = "job_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    role: Mapped[str] = mapped_column(String(512), nullable=False)
    company: Mapped[str] = mapped_column(String(512), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(120), nullable=False)
    posted: Mapped[str] = mapped_column(String(32), nullable=False)
    rate: Mapped[Optional[str]] = mapped_column(String(120))
    match: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    skills: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    portal_name: Mapped[Optional[str]] = mapped_column(String(120))
    portal_url: Mapped[Optional[str]] = mapped_column(String(1024))
    source_url: Mapped[Optional[str]] = mapped_column(String(1024))
    description: Mapped[Optional[str]] = mapped_column(Text)


class SavedJob(Base):
    __tablename__ = "saved_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_result_id: Mapped[int] = mapped_column(ForeignKey("job_results.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "job_result_id", name="uq_saved_jobs_user_job"),)


class JobApplication(Base, TimestampMixin):
    __tablename__ = "job_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    job_result_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job_results.id", ondelete="SET NULL"))
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    stage: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_label: Mapped[str] = mapped_column(String(64), nullable=False)
    action_label: Mapped[str] = mapped_column(String(255), nullable=False)
    portal: Mapped[Optional[str]] = mapped_column(String(120))
    application_date: Mapped[Optional[date]] = mapped_column(Date)
    match: Mapped[Optional[int]] = mapped_column(Integer)
    posting_url: Mapped[Optional[str]] = mapped_column(String(512))
    # Supervised portal-apply lifecycle: queued → filling → needs_attention → awaiting_submit → applied|failed|manual
    attempt_status: Mapped[str] = mapped_column(String(64), default="manual", nullable=False)
    attempt_detail: Mapped[str] = mapped_column(Text, default="", nullable=False)
    confirmation_url: Mapped[Optional[str]] = mapped_column(String(512))


class TailoredResume(Base, TimestampMixin):
    __tablename__ = "tailored_resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_result_id: Mapped[int] = mapped_column(ForeignKey("job_results.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "job_result_id", name="uq_tailored_resumes_user_job"),)


class LinkedInJob(Base, TimestampMixin):
    __tablename__ = "linkedin_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(120), nullable=False)
    type: Mapped[Optional[str]] = mapped_column(String(64))
    posted: Mapped[Optional[str]] = mapped_column(String(32))
    match: Mapped[Optional[int]] = mapped_column(Integer)
    easy_apply: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    applicants: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    insight: Mapped[Optional[str]] = mapped_column(Text)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(512))
    experience_level: Mapped[Optional[str]] = mapped_column(String(32))
    date_posted: Mapped[Optional[str]] = mapped_column(String(32))


class JobAnalysis(Base, TimestampMixin):
    __tablename__ = "job_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_result_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job_results.id", ondelete="SET NULL"))
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    tailored_score: Mapped[Optional[int]] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    hits: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    misses: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    suggestions: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    skill_gaps: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    recommendations: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    experience_match: Mapped[Optional[str]] = mapped_column(Text)
    title_match: Mapped[Optional[str]] = mapped_column(Text)
    job_description: Mapped[Optional[str]] = mapped_column(Text)


# ─── LinkedIn recruiter ───────────────────────────────────────────────────────


class LinkedInRecruiter(Base, TimestampMixin):
    __tablename__ = "linkedin_recruiters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    external_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(120), nullable=False)
    techs: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    connection_degree: Mapped[str] = mapped_column(String(16), default="2nd", nullable=False)
    avatar: Mapped[Optional[str]] = mapped_column(String(8))
    match_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="LinkedIn", nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    note: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="new", nullable=False)
    bookmarked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    contacted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    replied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class LinkedInSequence(Base, TimestampMixin):
    __tablename__ = "linkedin_sequences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    external_id: Mapped[Optional[int]] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    recruiter_id: Mapped[Optional[int]] = mapped_column(ForeignKey("linkedin_recruiters.id", ondelete="SET NULL"))

    steps: Mapped[list["LinkedInSequenceStep"]] = relationship(back_populates="sequence", cascade="all, delete-orphan")


class LinkedInSequenceStep(Base):
    __tablename__ = "linkedin_sequence_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sequence_id: Mapped[int] = mapped_column(ForeignKey("linkedin_sequences.id", ondelete="CASCADE"), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    step_date: Mapped[Optional[str]] = mapped_column(String(32))

    sequence: Mapped["LinkedInSequence"] = relationship(back_populates="steps")


class LinkedInFollowup(Base, TimestampMixin):
    __tablename__ = "linkedin_followups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    due: Mapped[str] = mapped_column(String(64), nullable=False)
    followup_type: Mapped[str] = mapped_column(String(64), nullable=False)


class LinkedInMessageTemplate(Base, TimestampMixin):
    __tablename__ = "linkedin_message_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)


class LinkedInOutreachQueue(Base, TimestampMixin):
    __tablename__ = "linkedin_outreach_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    recruiter_ids: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="scheduled", index=True, nullable=False)


class LinkedInSettings(Base, TimestampMixin):
    __tablename__ = "linkedin_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    auto_run_daily: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_enrich: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    skip_contacted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_followup: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ai_personalize: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_per_day: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    delay_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    account_email: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    daily_connections: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    daily_inmails: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    respect_dnc: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    honor_unsubscribes: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    use_permitted_sources: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class LinkedInApiSource(Base, TimestampMixin):
    __tablename__ = "linkedin_api_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    short_code: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="disconnected", nullable=False)
    color: Mapped[str] = mapped_column(String(16), default="#6b7280", nullable=False)


class LinkedInApiKey(Base, TimestampMixin):
    __tablename__ = "linkedin_api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    api_key: Mapped[str] = mapped_column(String(512), nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_linkedin_api_keys_user_provider"),)


# ─── Reporting ──────────────────────────────────────────────────────────────


class DayReportRow(Base, TimestampMixin):
    __tablename__ = "day_report_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    recruiter: Mapped[str] = mapped_column(String(120), nullable=False)
    technology: Mapped[str] = mapped_column(String(255), nullable=False)
    linkedin: Mapped[Optional[int]] = mapped_column(Integer)
    calls: Mapped[Optional[int]] = mapped_column(Integer)
    sourced: Mapped[Optional[int]] = mapped_column(Integer)
    marketing: Mapped[Optional[int]] = mapped_column(Integer)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class SubmissionMonth(Base, TimestampMixin):
    __tablename__ = "submission_months"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    month: Mapped[str] = mapped_column(String(7), unique=True, index=True, nullable=False)
    submissions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    placement_rate: Mapped[Optional[float]] = mapped_column(Float)


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(255))
    body: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(128))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# Backward-compatible aliases for legacy scripts
Campaign = CampaignItem
Contact = CampaignContact
