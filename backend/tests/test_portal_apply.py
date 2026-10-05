"""Complete multi-portal Quick Apply test cases.

Covers: portal detection, registry routing, demo/manual modes, missing URL,
apply/submit labels, and Playwright mock Easy Apply → Applied for all boards.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import get_settings
from app.services.portal_apply.base import ApplicantPayload, JobApplyTarget
from app.services.portal_apply.dice import DiceApplyAdapter, is_dice_target
from app.services.portal_apply.job_board import JobBoardApplyAdapter, is_job_board_target
from app.services.portal_apply.portals import (
    PORTAL_SPECS,
    detect_portal,
    is_supported_portal,
    portal_label,
    supported_portal_labels,
)
from app.services.portal_apply.registry import resolve_adapter

FIXTURE = Path(__file__).parent / "fixtures" / "dice_easy_apply_mock.html"

SUPPORTED_CASES = [
    ("Dice", "https://www.dice.com/job-detail/abc", "dice", "Dice"),
    ("CareerBuilder", "https://www.careerbuilder.com/job/jd123", "careerbuilder", "CareerBuilder"),
    ("Monster", "https://www.monster.com/job-openings/abc", "monster", "Monster"),
    ("Indeed", "https://www.indeed.com/viewjob?jk=1", "indeed", "Indeed"),
    ("ZipRecruiter", "https://www.ziprecruiter.com/jobs/1", "ziprecruiter", "ZipRecruiter"),
    ("LinkedIn", "https://www.linkedin.com/jobs/view/1", "linkedin", "LinkedIn"),
]

VIEW_ON_CASES = [
    ("View on CareerBuilder", "https://www.careerbuilder.com/job/1", "careerbuilder"),
    ("View on Monster", "https://www.monster.com/jobs/1", "monster"),
    ("View on Dice", "https://www.dice.com/job-detail/1", "dice"),
    ("View on Indeed", "https://www.indeed.com/viewjob?jk=9", "indeed"),
]

URL_ONLY_CASES = [
    ("", "https://www.dice.com/jobs?q=java", "dice"),
    ("Other", "https://www.careerbuilder.com/jobs/x", "careerbuilder"),
    ("Board", "https://www.monster.com/job/x", "monster"),
    ("", "https://www.ziprecruiter.com/c/x", "ziprecruiter"),
]

APPLICANT = ApplicantPayload(
    name="Test Candidate",
    email="test.candidate@email.com",
    phone="+1 (555) 555-0128",
    location="Dallas, TX",
    linkedin="https://linkedin.com/in/testcandidate",
    experience="5-8 Years",
)


# ---------------------------------------------------------------------------
# TC-PA-01 … detection
# ---------------------------------------------------------------------------


class TestPortalDetection:
    """TC-PA-01: Detect each supported portal from name and/or URL."""

    @pytest.mark.parametrize("portal_name,url,key,label", SUPPORTED_CASES)
    def test_detect_by_name_and_url(self, portal_name, url, key, label):
        spec = detect_portal(portal_name, url)
        assert spec is not None
        assert spec.key == key
        assert spec.label == label
        assert is_supported_portal(portal_name, url)
        assert is_job_board_target(portal_name, url)
        assert portal_label(portal_name, url) == label

    @pytest.mark.parametrize("portal_name,url,key", VIEW_ON_CASES)
    def test_detect_view_on_portal_labels(self, portal_name, url, key):
        spec = detect_portal(portal_name, url)
        assert spec is not None
        assert spec.key == key

    @pytest.mark.parametrize("portal_name,url,key", URL_ONLY_CASES)
    def test_detect_from_url_when_name_generic(self, portal_name, url, key):
        assert detect_portal(portal_name, url).key == key

    def test_unknown_portal_not_supported(self):
        assert detect_portal("Company Careers", "https://careers.example.com/job/1") is None
        assert not is_supported_portal("Direct", "https://example.com/careers/1")
        assert not is_job_board_target("Direct", "https://example.com/careers/1")
        assert portal_label("Acme Careers", "https://acme.test/jobs/1") == "Acme Careers"
        assert portal_label("", "", fallback="Portal") == "Portal"

    def test_dice_compat_helpers(self):
        assert is_dice_target("Dice", "https://www.dice.com/job-detail/abc")
        assert is_dice_target("Other", "https://www.dice.com/jobs?q=java")
        assert not is_dice_target("Monster", "https://www.monster.com/jobs")

    def test_supported_portal_catalog(self):
        labels = supported_portal_labels()
        assert labels == [spec.label for spec in PORTAL_SPECS]
        assert set(labels) >= {"Dice", "CareerBuilder", "Monster", "Indeed", "ZipRecruiter", "LinkedIn"}
        for spec in PORTAL_SPECS:
            assert spec.apply_labels
            assert spec.submit_labels


# ---------------------------------------------------------------------------
# TC-PA-02 … registry
# ---------------------------------------------------------------------------


class TestAdapterRegistry:
    """TC-PA-02: Supported boards → JobBoardApplyAdapter; unknown → Manual."""

    @pytest.mark.parametrize("portal_name,url,key,label", SUPPORTED_CASES)
    def test_resolves_job_board_adapter(self, portal_name, url, key, label):
        adapter = resolve_adapter(portal_name, url)
        assert adapter.portal_key == "job_board"
        assert adapter.supports(portal_name, url)
        assert label  # keep param used / readable in reports

    def test_falls_back_to_manual(self):
        adapter = resolve_adapter("Company Careers", "https://careers.example.com/job/1")
        assert adapter.portal_key == "manual"

    def test_dice_alias_is_job_board_adapter(self):
        assert DiceApplyAdapter is JobBoardApplyAdapter
        assert DiceApplyAdapter().portal_key == "job_board"


# ---------------------------------------------------------------------------
# TC-PA-03 … demo / manual / validation modes
# ---------------------------------------------------------------------------


class TestApplyModes:
    """TC-PA-03: Demo marks Applied; manual tracks; missing URL fails."""

    @pytest.mark.parametrize("portal_name,url,key,label", SUPPORTED_CASES)
    def test_demo_mode_marks_applied_for_each_portal(self, monkeypatch, portal_name, url, key, label):
        monkeypatch.setenv("PORTAL_APPLY_MODE", "demo")
        get_settings.cache_clear()
        try:
            result = JobBoardApplyAdapter().apply(
                JobApplyTarget(
                    job_id=1,
                    role="Java Developer",
                    company="Acme",
                    portal_name=portal_name,
                    posting_url=url,
                ),
                ApplicantPayload(name="Test User", email="test@example.com"),
            )
            assert result.attempt_status == "applied"
            assert result.status == "Applied"
            assert label in (result.stage or "") or "demo" in (result.stage or "").lower()
            assert key  # report clarity
        finally:
            get_settings.cache_clear()

    def test_manual_mode_tracks_without_browser(self, monkeypatch):
        monkeypatch.setenv("PORTAL_APPLY_MODE", "manual")
        get_settings.cache_clear()
        try:
            result = JobBoardApplyAdapter().apply(
                JobApplyTarget(
                    job_id=2,
                    role="Data Engineer",
                    company="Acme",
                    portal_name="Monster",
                    posting_url="https://www.monster.com/job/demo",
                ),
                ApplicantPayload(name="Test User", email="test@example.com"),
            )
            assert result.attempt_status in {"manual", "applied"}
            assert result.status in {"Applied", "Action Needed"}
            assert result.open_url or result.detail
        finally:
            get_settings.cache_clear()

    def test_missing_url_fails_in_supervised_mode(self, monkeypatch):
        monkeypatch.setenv("PORTAL_APPLY_MODE", "supervised")
        get_settings.cache_clear()
        try:
            result = JobBoardApplyAdapter().apply(
                JobApplyTarget(
                    job_id=3,
                    role="Engineer",
                    company="Acme",
                    portal_name="CareerBuilder",
                    posting_url="",
                ),
                ApplicantPayload(name="Test User", email="test@example.com"),
            )
            assert result.attempt_status == "failed"
            assert "CareerBuilder" in (result.stage or result.detail or "")
        finally:
            get_settings.cache_clear()

    def test_apply_and_submit_labels_include_portal_specifics(self):
        adapter = JobBoardApplyAdapter()
        for portal_name, url, _key, label in SUPPORTED_CASES:
            job = JobApplyTarget(
                job_id=1,
                role="Role",
                company="Co",
                portal_name=portal_name,
                posting_url=url,
            )
            apply_labels = adapter._apply_labels_for(job)
            submit_labels = adapter._submit_labels_for(job)
            assert apply_labels
            assert submit_labels
            assert "Apply" in " ".join(apply_labels) or "Easy Apply" in apply_labels
            assert any("Submit" in item or item in {"Next", "Continue", "Finish"} for item in submit_labels)
            assert label


# ---------------------------------------------------------------------------
# TC-PA-04 … Playwright mock Easy Apply → Applied
# ---------------------------------------------------------------------------


@pytest.mark.playwright
class TestPlaywrightMockApply:
    """TC-PA-04: Local Easy Apply mock auto-submits and returns Applied."""

    @pytest.mark.parametrize(
        "portal_name,expected_label",
        [(name, label) for name, _url, _key, label in SUPPORTED_CASES],
    )
    def test_mock_easy_apply_auto_submits(self, monkeypatch, portal_name, expected_label):
        assert FIXTURE.exists(), f"Missing fixture: {FIXTURE}"

        monkeypatch.setenv("PORTAL_APPLY_MODE", "supervised")
        monkeypatch.setenv("PORTAL_APPLY_AUTO_SUBMIT", "true")
        monkeypatch.setenv("PLAYWRIGHT_HEADLESS", "true")
        monkeypatch.setenv("PORTAL_APPLY_TIMEOUT_SECONDS", "60")
        browsers = Path.cwd() / ".playwright-browsers"
        if browsers.exists():
            monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(browsers.resolve()))
        get_settings.cache_clear()

        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
        except ImportError:
            pytest.skip("Playwright package not installed")

        try:
            result = JobBoardApplyAdapter()._run_supervised_browser(
                JobApplyTarget(
                    job_id=99,
                    role="Big Data Engineer",
                    company="Greecy Infotech",
                    portal_name=portal_name,
                    posting_url=FIXTURE.resolve().as_uri(),
                ),
                APPLICANT,
            )
            assert result.attempt_status == "applied", result.detail
            assert result.status == "Applied", result.detail
            assert expected_label in (result.stage or "") or "Submitted" in (result.stage or "")
        finally:
            get_settings.cache_clear()
