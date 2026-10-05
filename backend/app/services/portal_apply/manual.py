"""Manual fallback — track application and return a portal URL for the UI to open."""

from __future__ import annotations

from typing import Optional

from app.services.portal_apply.base import (
    ApplicantPayload,
    ApplyResult,
    JobApplyTarget,
    ProgressCallback,
)


class ManualApplyAdapter:
    portal_key = "manual"

    def supports(self, portal_name: str, posting_url: str) -> bool:
        return True

    def apply(
        self,
        job: JobApplyTarget,
        applicant: ApplicantPayload,
        *,
        on_progress: Optional[ProgressCallback] = None,
    ) -> ApplyResult:
        if on_progress:
            on_progress("manual", "Opening portal for manual completion.")
        portal = job.portal_name or "Portal"
        return ApplyResult(
            attempt_status="manual",
            status="Applied",
            stage=f"Opened on {portal} — complete submission in the browser",
            action_label="Confirm recruiter response",
            detail=(
                f"Profile ({applicant.name or 'candidate'}) and CV metadata were prepared. "
                f"Complete the application on {portal}, then verify status in Tracker."
            ),
            open_url=job.posting_url or None,
        )
