"""Supported job-board portals for supervised Quick Apply."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PortalSpec:
    key: str
    label: str
    name_tokens: tuple[str, ...]
    url_tokens: tuple[str, ...]
    apply_labels: tuple[str, ...] = ()
    submit_labels: tuple[str, ...] = ()


PORTAL_SPECS: tuple[PortalSpec, ...] = (
    PortalSpec(
        key="dice",
        label="Dice",
        name_tokens=("dice",),
        url_tokens=("dice.com",),
        apply_labels=("Easy Apply", "Apply Now", "Apply"),
        submit_labels=("Submit Application", "Submit", "Next", "Continue"),
    ),
    PortalSpec(
        key="careerbuilder",
        label="CareerBuilder",
        name_tokens=("careerbuilder", "career builder"),
        url_tokens=("careerbuilder.com",),
        apply_labels=("Apply Now", "Easy Apply", "Quick Apply", "Apply", "Start Application"),
        submit_labels=("Submit Application", "Submit", "Continue", "Next", "Finish"),
    ),
    PortalSpec(
        key="monster",
        label="Monster",
        name_tokens=("monster",),
        url_tokens=("monster.com",),
        apply_labels=("Apply Now", "Quick Apply", "Easy Apply", "Apply", "1-Click Apply"),
        submit_labels=("Submit Application", "Submit", "Continue", "Next", "Send Application"),
    ),
    PortalSpec(
        key="indeed",
        label="Indeed",
        name_tokens=("indeed",),
        url_tokens=("indeed.com",),
        apply_labels=("Indeed Apply", "Apply now", "Apply Now", "Easy Apply", "Apply"),
        submit_labels=("Continue", "Submit", "Submit application", "Review your application", "Next"),
    ),
    PortalSpec(
        key="ziprecruiter",
        label="ZipRecruiter",
        name_tokens=("ziprecruiter", "zip recruiter"),
        url_tokens=("ziprecruiter.com",),
        apply_labels=("Apply Now", "1-Click Apply", "Easy Apply", "Apply"),
        submit_labels=("Submit", "Submit Application", "Continue", "Next", "Finish"),
    ),
    PortalSpec(
        key="linkedin",
        label="LinkedIn",
        name_tokens=("linkedin",),
        url_tokens=("linkedin.com",),
        apply_labels=("Easy Apply", "Apply", "Continue"),
        submit_labels=("Submit application", "Submit", "Review", "Next", "Continue"),
    ),
)


def detect_portal(portal_name: str, posting_url: str) -> Optional[PortalSpec]:
    haystack = f"{portal_name or ''} {posting_url or ''}".lower()
    for spec in PORTAL_SPECS:
        if any(token in haystack for token in spec.name_tokens):
            return spec
        if any(token in haystack for token in spec.url_tokens):
            return spec
    return None


def is_supported_portal(portal_name: str, posting_url: str) -> bool:
    return detect_portal(portal_name, posting_url) is not None


def portal_label(portal_name: str, posting_url: str, fallback: str = "Portal") -> str:
    spec = detect_portal(portal_name, posting_url)
    if spec:
        return spec.label
    name = (portal_name or "").strip()
    return name or fallback


def supported_portal_labels() -> list[str]:
    return [spec.label for spec in PORTAL_SPECS]
