"""Shared types for portal application adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Protocol


@dataclass
class ApplicantPayload:
    """Profile + CV data collected for a portal application."""

    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    experience: str = ""
    employment_type: str = ""
    rate: str = ""
    visa: str = ""
    work_mode: str = ""
    summary: str = ""
    skills: list[str] = field(default_factory=list)
    job_titles: list[str] = field(default_factory=list)
    resume_file_name: str = "resume.pdf"
    resume_content_type: str = "application/pdf"
    resume_bytes: Optional[bytes] = None


@dataclass
class JobApplyTarget:
    job_id: int
    role: str
    company: str
    portal_name: str
    posting_url: str
    description: str = ""


@dataclass
class ApplyResult:
    """Outcome of a supervised or manual portal apply attempt."""

    attempt_status: str  # queued|filling|needs_attention|awaiting_submit|applied|failed|manual
    status: str  # Tracker status: Applying|Applied|Failed|Action Needed
    stage: str
    action_label: str
    detail: str = ""
    confirmation_url: Optional[str] = None
    open_url: Optional[str] = None


ProgressCallback = Callable[[str, str], None]


class PortalApplyAdapter(Protocol):
    portal_key: str

    def supports(self, portal_name: str, posting_url: str) -> bool: ...

    def apply(
        self,
        job: JobApplyTarget,
        applicant: ApplicantPayload,
        *,
        on_progress: Optional[ProgressCallback] = None,
    ) -> ApplyResult: ...
