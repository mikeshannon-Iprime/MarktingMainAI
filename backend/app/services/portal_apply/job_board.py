"""Job-board supervised apply (Dice, CareerBuilder, Monster, Indeed, ZipRecruiter, LinkedIn).

Uses headed Playwright in a child process (Windows/uvicorn-safe).
"""

from __future__ import annotations

import asyncio
import logging
import multiprocessing as mp
import re
import sys
import tempfile
import time
import webbrowser
from dataclasses import asdict
from pathlib import Path
from queue import Empty
from typing import Any, Optional
from urllib.parse import urlparse

from app.core.config import get_settings
from app.services.portal_apply.base import (
    ApplicantPayload,
    ApplyResult,
    JobApplyTarget,
    ProgressCallback,
)
from app.services.portal_apply.portals import (
    PortalSpec,
    detect_portal,
    is_supported_portal,
    portal_label,
)

logger = logging.getLogger(__name__)

LOGIN_HINTS = re.compile(r"(sign.?in|log.?in|auth|captcha|verify|challenge)", re.I)
SUCCESS_HINTS = re.compile(
    r"(application (submitted|sent|received|complete)|thank you for applying|successfully applied|you.?ve applied)",
    re.I,
)
DEFAULT_APPLY_BUTTON_LABELS = (
    "Easy Apply",
    "Indeed Apply",
    "1-Click Apply",
    "Quick Apply",
    "Apply Now",
    "Apply now",
    "Apply",
    "Continue Application",
    "Start Application",
)
DEFAULT_SUBMIT_BUTTON_LABELS = (
    "Submit Application",
    "Submit application",
    "Send Application",
    "Submit",
    "Finish",
    "Complete Application",
    "Next",
    "Continue",
    "Review and Submit",
    "Review your application",
)


def is_dice_target(portal_name: str, posting_url: str) -> bool:
    """Backward-compatible Dice detector."""
    spec = detect_portal(portal_name, posting_url)
    return bool(spec and spec.key == "dice")


def is_job_board_target(portal_name: str, posting_url: str) -> bool:
    return is_supported_portal(portal_name, posting_url)


def _applicant_to_dict(applicant: ApplicantPayload) -> dict[str, Any]:
    return {
        "name": applicant.name,
        "email": applicant.email,
        "phone": applicant.phone,
        "location": applicant.location,
        "linkedin": applicant.linkedin,
        "experience": applicant.experience,
        "employment_type": applicant.employment_type,
        "rate": applicant.rate,
        "visa": applicant.visa,
        "work_mode": applicant.work_mode,
        "summary": applicant.summary,
        "skills": list(applicant.skills or []),
        "job_titles": list(applicant.job_titles or []),
        "resume_file_name": applicant.resume_file_name,
        "resume_content_type": applicant.resume_content_type,
        "resume_bytes": applicant.resume_bytes,
    }


def _applicant_from_dict(data: dict[str, Any]) -> ApplicantPayload:
    return ApplicantPayload(**data)


def _job_to_dict(job: JobApplyTarget) -> dict[str, Any]:
    return asdict(job)


def _job_from_dict(data: dict[str, Any]) -> JobApplyTarget:
    return JobApplyTarget(**data)


def _result_from_dict(data: dict[str, Any]) -> ApplyResult:
    return ApplyResult(**data)


def _label_for(job: JobApplyTarget) -> str:
    return portal_label(job.portal_name, job.posting_url, fallback=job.portal_name or "Portal")


def _spec_for(job: JobApplyTarget) -> Optional[PortalSpec]:
    return detect_portal(job.portal_name, job.posting_url)


def _manual_fallback(job: JobApplyTarget, applicant: ApplicantPayload, reason: str) -> ApplyResult:
    label = _label_for(job)
    try:
        if job.posting_url:
            webbrowser.open(job.posting_url, new=2)
    except Exception:
        logger.exception("Could not open system browser for %s URL", label)

    from app.services.portal_apply.manual import ManualApplyAdapter

    result = ManualApplyAdapter().apply(job, applicant)
    result.detail = (
        f"{reason} Opened {label} in your default browser — complete Submit there, then check Tracker. "
        f"{result.detail}"
    )
    result.open_url = job.posting_url
    return result


def _job_board_worker_main(job_data: dict, applicant_data: dict, queue: mp.Queue) -> None:
    import os

    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass

    try:
        settings = get_settings()
        configured = (settings.playwright_browsers_path or "").strip() or ".playwright-browsers"
        browsers_path = Path(configured)
        if not browsers_path.is_absolute():
            browsers_path = Path.cwd() / browsers_path
        if browsers_path.exists():
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path.resolve())
    except Exception:
        pass

    def on_progress(status: str, detail: str) -> None:
        try:
            queue.put({"type": "progress", "status": status, "detail": detail})
        except Exception:
            pass

    try:
        job = _job_from_dict(job_data)
        applicant = _applicant_from_dict(applicant_data)
        result = JobBoardApplyAdapter()._run_supervised_browser(job, applicant, on_progress=on_progress)
        queue.put(
            {
                "type": "result",
                "result": {
                    "attempt_status": result.attempt_status,
                    "status": result.status,
                    "stage": result.stage,
                    "action_label": result.action_label,
                    "detail": result.detail,
                    "confirmation_url": result.confirmation_url,
                    "open_url": result.open_url,
                },
            }
        )
    except Exception as exc:
        logger.exception("Job-board apply worker crashed")
        queue.put(
            {
                "type": "result",
                "result": {
                    "attempt_status": "failed",
                    "status": "Failed",
                    "stage": "Portal apply worker error",
                    "action_label": "Retry Quick Apply",
                    "detail": str(exc),
                    "confirmation_url": None,
                    "open_url": job_data.get("posting_url"),
                },
            }
        )


class JobBoardApplyAdapter:
    """Supervised apply for Dice, CareerBuilder, Monster, Indeed, ZipRecruiter, LinkedIn."""

    portal_key = "job_board"

    def supports(self, portal_name: str, posting_url: str) -> bool:
        return is_supported_portal(portal_name, posting_url)

    def apply(
        self,
        job: JobApplyTarget,
        applicant: ApplicantPayload,
        *,
        on_progress: Optional[ProgressCallback] = None,
    ) -> ApplyResult:
        settings = get_settings()
        mode = (settings.portal_apply_mode or "supervised").lower()
        label = _label_for(job)

        if mode == "demo":
            if on_progress:
                on_progress("applied", f"Demo mode — marked Applied without opening {label}.")
            return ApplyResult(
                attempt_status="applied",
                status="Applied",
                stage=f"{label} demo apply completed",
                action_label="Await recruiter response",
                detail=f"PORTAL_APPLY_MODE=demo — no live {label} interaction.",
                confirmation_url=job.posting_url,
            )

        if mode == "manual":
            return _manual_fallback(job, applicant, "Manual apply mode.")

        try:
            import playwright  # noqa: F401
        except ImportError:
            return _manual_fallback(
                job,
                applicant,
                "Playwright is not installed. Run: pip install playwright && playwright install chromium.",
            )

        if not job.posting_url or not (
            job.posting_url.startswith("http") or job.posting_url.startswith("file:")
        ):
            return ApplyResult(
                attempt_status="failed",
                status="Failed",
                stage=f"Missing {label} job URL",
                action_label="Re-run search for a live portal posting",
                detail=f"This job does not include a valid {label} application URL.",
            )

        return self._run_supervised_via_process(job, applicant, on_progress=on_progress)

    def _run_supervised_via_process(
        self,
        job: JobApplyTarget,
        applicant: ApplicantPayload,
        *,
        on_progress: Optional[ProgressCallback] = None,
    ) -> ApplyResult:
        settings = get_settings()
        timeout_seconds = max(60, int(settings.portal_apply_timeout_seconds) + 30)
        label = _label_for(job)

        if on_progress:
            on_progress("filling", f"Launching {label} browser (separate process)…")

        ctx = mp.get_context("spawn")
        queue: mp.Queue = ctx.Queue()
        proc = ctx.Process(
            target=_job_board_worker_main,
            args=(_job_to_dict(job), _applicant_to_dict(applicant), queue),
            daemon=True,
            name=f"portal-apply-{job.job_id}",
        )
        proc.start()

        result_data: Optional[dict] = None
        deadline = time.time() + timeout_seconds
        try:
            while time.time() < deadline:
                try:
                    message = queue.get(timeout=1.0)
                except Empty:
                    if not proc.is_alive():
                        try:
                            message = queue.get_nowait()
                        except Empty:
                            break
                    else:
                        continue

                if message.get("type") == "progress":
                    if on_progress:
                        on_progress(message.get("status") or "filling", message.get("detail") or "")
                elif message.get("type") == "result":
                    result_data = message.get("result")
                    break
        finally:
            if proc.is_alive():
                proc.join(timeout=5)
            if proc.is_alive():
                proc.terminate()
                proc.join(timeout=3)

        if result_data:
            result = _result_from_dict(result_data)
            if result.attempt_status == "failed" and "NotImplementedError" in (result.detail or ""):
                return _manual_fallback(
                    job,
                    applicant,
                    "Playwright could not start from the API worker thread.",
                )
            if result.attempt_status == "failed" and any(
                token in (result.detail or "").lower()
                for token in ("chromium", "browser", "executable", "playwright")
            ):
                return _manual_fallback(
                    job,
                    applicant,
                    f"{label} browser automation failed ({result.detail}).",
                )
            return result

        return _manual_fallback(job, applicant, f"{label} browser process exited without a result.")

    def _profile_dir_for(self, job: JobApplyTarget) -> Path:
        settings = get_settings()
        spec = _spec_for(job)
        key = spec.key if spec else "generic"
        base = Path(settings.portal_apply_profile_dir)
        root = base.parent if (base.name.endswith("-profile") or base.name == "dice-profile") else base
        profile_dir = root / f"{key}-profile"
        if not profile_dir.is_absolute():
            profile_dir = Path.cwd() / profile_dir
        profile_dir.mkdir(parents=True, exist_ok=True)
        return profile_dir

    def _apply_labels_for(self, job: JobApplyTarget) -> tuple[str, ...]:
        spec = _spec_for(job)
        extra = spec.apply_labels if spec else ()
        return tuple(dict.fromkeys([*extra, *DEFAULT_APPLY_BUTTON_LABELS]))

    def _submit_labels_for(self, job: JobApplyTarget) -> tuple[str, ...]:
        spec = _spec_for(job)
        extra = spec.submit_labels if spec else ()
        return tuple(dict.fromkeys([*extra, *DEFAULT_SUBMIT_BUTTON_LABELS]))

    def _run_supervised_browser(
        self,
        job: JobApplyTarget,
        applicant: ApplicantPayload,
        *,
        on_progress: Optional[ProgressCallback] = None,
    ) -> ApplyResult:
        from playwright.sync_api import TimeoutError as PlaywrightTimeout
        from playwright.sync_api import sync_playwright

        settings = get_settings()
        timeout_ms = max(30, int(settings.portal_apply_timeout_seconds)) * 1000
        profile_dir = self._profile_dir_for(job)
        label = _label_for(job)

        def progress(status: str, detail: str) -> None:
            logger.info("%s apply [%s]: %s", label, status, detail)
            if on_progress:
                on_progress(status, detail)

        resume_path: Optional[Path] = None
        try:
            if applicant.resume_bytes:
                suffix = Path(applicant.resume_file_name or "resume.pdf").suffix or ".pdf"
                handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                handle.write(applicant.resume_bytes)
                handle.close()
                resume_path = Path(handle.name)

            with sync_playwright() as playwright:
                try:
                    context = playwright.chromium.launch_persistent_context(
                        user_data_dir=str(profile_dir),
                        headless=bool(settings.playwright_headless),
                        viewport={"width": 1280, "height": 900},
                        accept_downloads=True,
                    )
                except Exception as launch_exc:
                    logger.warning("Chromium launch failed: %s", launch_exc)
                    return ApplyResult(
                        attempt_status="failed",
                        status="Failed",
                        stage="Could not launch Chromium",
                        action_label="Install Chromium then retry",
                        detail=str(launch_exc),
                        open_url=job.posting_url,
                    )

                page = context.pages[0] if context.pages else context.new_page()
                page.set_default_timeout(15_000)

                progress("filling", f"Opening {label} posting for {job.role} at {job.company}.")
                page.goto(job.posting_url, wait_until="domcontentloaded", timeout=60_000)
                page.wait_for_timeout(1500)

                if self._looks_like_login(page):
                    progress(
                        "needs_attention",
                        f"{label} login or CAPTCHA detected. Sign in / solve the challenge in the browser window.",
                    )
                    self._wait_until(
                        page,
                        predicate=lambda: not self._looks_like_login(page),
                        timeout_ms=timeout_ms,
                        poll_ms=2000,
                    )

                apply_clicked = self._click_apply(page, job)
                if not apply_clicked:
                    progress(
                        "needs_attention",
                        f"Could not find an Apply button. Open Apply manually in the {label} window.",
                    )
                else:
                    page.wait_for_timeout(1200)

                filled_total = 0
                uploaded = False
                submitted = False
                auto_submit = bool(getattr(settings, "portal_apply_auto_submit", True))

                for step in range(1, 6):
                    if self._page_closed(page):
                        break
                    filled_total += self._fill_known_fields(page, applicant)
                    if resume_path and resume_path.exists() and not uploaded:
                        uploaded = self._upload_resume(page, resume_path)

                    if self._is_confirmed(page):
                        submitted = True
                        break

                    if auto_submit:
                        progress("filling", f"Auto-submitting {label} application (step {step})…")
                        clicked = self._click_submit(page, job)
                        if clicked:
                            submitted = True
                            page.wait_for_timeout(1500)
                            if self._is_confirmed(page):
                                break
                            continue
                        progress(
                            "needs_attention",
                            f"Could not find Submit. Complete Submit in the {label} window if shown.",
                        )
                        break

                    progress(
                        "awaiting_submit",
                        (
                            f"Auto-filled {filled_total} field(s)"
                            + (" and attached your CV" if uploaded else "")
                            + f". Review answers, then click Submit on {label}."
                        ),
                    )
                    break

                if auto_submit and submitted and not self._page_closed(page) and not self._is_confirmed(page):
                    progress("awaiting_submit", f"Submit clicked — waiting for {label} confirmation…")
                    self._wait_for_confirmation(page, timeout_ms=min(timeout_ms, 120_000))
                elif not auto_submit:
                    progress(
                        "awaiting_submit",
                        (
                            f"Auto-filled {filled_total} field(s)"
                            + (" and attached your CV" if uploaded else "")
                            + f". Click Submit on {label}. Waiting for confirmation…"
                        ),
                    )
                    self._wait_for_confirmation(page, timeout_ms=timeout_ms)

                confirmed = False if self._page_closed(page) else self._is_confirmed(page)
                if not confirmed and auto_submit and submitted:
                    confirmed = True
                    detail = (
                        f"Auto-submitted on {label} after filling {filled_total} field(s)"
                        + (" and uploading CV" if uploaded else "")
                        + "."
                    )
                else:
                    detail = f"{label} confirmed the application after automated Submit."

                current_url = None
                try:
                    if not self._page_closed(page):
                        current_url = page.url
                except Exception:
                    current_url = job.posting_url

                try:
                    if not self._page_closed(page):
                        page.close()
                except Exception:
                    pass
                try:
                    context.close()
                except Exception:
                    pass

                if confirmed:
                    return ApplyResult(
                        attempt_status="applied",
                        status="Applied",
                        stage=f"Submitted on {label}",
                        action_label="Await recruiter response",
                        detail=detail,
                        confirmation_url=current_url or job.posting_url,
                    )

                return ApplyResult(
                    attempt_status="failed",
                    status="Action Needed",
                    stage=f"{label} apply timed out before confirmation",
                    action_label=f"Retry Quick Apply or finish on {label}",
                    detail=(
                        f"No {label} confirmation within {settings.portal_apply_timeout_seconds}s. "
                        "If you already submitted, mark the Tracker item manually."
                    ),
                    confirmation_url=current_url,
                    open_url=job.posting_url,
                )
        except PlaywrightTimeout as exc:
            logger.exception("%s supervised apply timed out", label)
            return ApplyResult(
                attempt_status="failed",
                status="Failed",
                stage=f"{label} page timed out",
                action_label="Retry Quick Apply",
                detail=str(exc),
                open_url=job.posting_url,
            )
        except Exception as exc:
            message = str(exc)
            if "TargetClosedError" in message or "has been closed" in message.lower():
                return ApplyResult(
                    attempt_status="failed",
                    status="Action Needed",
                    stage=f"{label} browser page closed",
                    action_label=f"Reopen {label} and submit manually",
                    detail=f"{label} browser page closed before confirmation.",
                    open_url=job.posting_url,
                )
            logger.exception("%s supervised apply failed", label)
            return ApplyResult(
                attempt_status="failed",
                status="Failed",
                stage=f"{label} automation error",
                action_label="Retry Quick Apply or apply manually",
                detail=message,
                open_url=job.posting_url,
            )
        finally:
            if resume_path and resume_path.exists():
                try:
                    resume_path.unlink()
                except OSError:
                    pass

    def _page_closed(self, page) -> bool:
        try:
            return page.is_closed()
        except Exception:
            return True

    def _is_confirmed(self, page) -> bool:
        try:
            if self._page_closed(page):
                return False
            url = (page.url or "").lower()
            if any(token in url for token in ("confirm", "thank", "success", "applied")):
                return True
            text = page.locator("body").inner_text(timeout=2000)
            return bool(SUCCESS_HINTS.search(text[:8000]))
        except Exception:
            return False

    def _click_apply(self, page, job: JobApplyTarget) -> bool:
        for label in self._apply_labels_for(job):
            selectors = [
                f"button:has-text('{label}')",
                f"a:has-text('{label}')",
                f"[role='button']:has-text('{label}')",
                f"input[type='submit'][value*='{label}']",
            ]
            for selector in selectors:
                try:
                    locator = page.locator(selector).first
                    if locator.count() and locator.is_visible():
                        locator.click(timeout=5000)
                        return True
                except Exception:
                    continue
        return False

    def _click_submit(self, page, job: JobApplyTarget) -> bool:
        for label in self._submit_labels_for(job):
            selectors = [
                f"button:has-text('{label}')",
                f"a:has-text('{label}')",
                f"[role='button']:has-text('{label}')",
                f"input[type='submit'][value*='{label}']",
                f"button[type='submit']:has-text('{label}')",
            ]
            for selector in selectors:
                try:
                    locator = page.locator(selector).first
                    if locator.count() and locator.is_visible():
                        locator.click(timeout=5000)
                        return True
                except Exception:
                    continue
        try:
            locator = page.locator("button[type='submit'], input[type='submit']").first
            if locator.count() and locator.is_visible():
                locator.click(timeout=5000)
                return True
        except Exception:
            pass
        return False

    def _looks_like_login(self, page) -> bool:
        try:
            url = page.url or ""
            path = urlparse(url).path.lower()
            if any(token in path for token in ("/login", "/signin", "/auth", "/challenge")):
                return True
            body = page.locator("body").inner_text(timeout=3000)
            return bool(LOGIN_HINTS.search(body[:4000])) and "apply" not in body.lower()[:500]
        except Exception:
            return False

    def _fill_known_fields(self, page, applicant: ApplicantPayload) -> int:
        mapping = [
            (("name", "full name", "first name", "candidate name"), applicant.name),
            (("email", "e-mail", "email address"), applicant.email),
            (("phone", "mobile", "telephone", "phone number"), applicant.phone),
            (("location", "city", "current location", "address"), applicant.location),
            (("linkedin", "linkedin url", "linkedin profile"), applicant.linkedin),
            (("experience", "years of experience", "total experience"), applicant.experience),
            (("rate", "pay rate", "desired rate", "salary"), applicant.rate),
            (("visa", "work authorization", "authorization"), applicant.visa),
        ]
        filled = 0
        for aliases, value in mapping:
            if not value:
                continue
            if self._fill_by_aliases(page, aliases, value):
                filled += 1
        return filled

    def _fill_by_aliases(self, page, aliases: tuple[str, ...], value: str) -> bool:
        for alias in aliases:
            selectors = [
                f"input[aria-label*='{alias}' i]",
                f"textarea[aria-label*='{alias}' i]",
                f"input[placeholder*='{alias}' i]",
                f"textarea[placeholder*='{alias}' i]",
                f"input[name*='{alias.replace(' ', '')}' i]",
                f"input[id*='{alias.replace(' ', '')}' i]",
                f"label:has-text('{alias}') >> .. >> input",
                f"label:has-text('{alias}') >> .. >> textarea",
            ]
            for selector in selectors:
                try:
                    locator = page.locator(selector).first
                    if locator.count() and locator.is_visible():
                        locator.fill(value, timeout=3000)
                        return True
                except Exception:
                    continue
        return False

    def _upload_resume(self, page, resume_path: Path) -> bool:
        try:
            inputs = page.locator("input[type='file']")
            count = inputs.count()
            for index in range(count):
                handle = inputs.nth(index)
                try:
                    handle.set_input_files(str(resume_path), timeout=5000)
                    return True
                except Exception:
                    continue
        except Exception:
            return False
        return False

    def _wait_for_confirmation(self, page, timeout_ms: int) -> bool:
        return self._wait_until(
            page,
            predicate=lambda: self._is_confirmed(page),
            timeout_ms=timeout_ms,
            poll_ms=2000,
        )

    def _wait_until(self, page, predicate, timeout_ms: int, poll_ms: int = 2000) -> bool:
        deadline = time.time() + (timeout_ms / 1000)
        while time.time() < deadline:
            try:
                if self._page_closed(page):
                    return False
                if predicate():
                    return True
            except Exception:
                pass
            try:
                page.wait_for_timeout(poll_ms)
            except Exception:
                return False
        return False


# Backward-compatible alias
DiceApplyAdapter = JobBoardApplyAdapter
