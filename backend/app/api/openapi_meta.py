"""OpenAPI / Swagger metadata for MarketingMind AI API."""

from __future__ import annotations

API_DESCRIPTION = """
MarketingMind AI production API for recruiting operations, campaign studio, and LinkedIn outreach.

## Job Automation match policy
Auto-apply scrapes **all configured portals** for posts in the last **24 hours** (`postedWithin=1`)
and **48 hours** (`postedWithin=2`), scores each role against the active CV, then routes:

| CV ↔ JD match | Action |
|---|---|
| **≥ 65%** | Auto-apply in background (no browser tab required from the UI) |
| **40–64%** | Tailor CV to the job description and track as `Tailoring` |
| **&lt; 40%** | Reject and track as `Rejected` |

Optional `matchThreshold` on auto-apply may **raise** the apply floor above 65%, never lower it.

## Apply eligibility
`POST /api/job-automation/apply` only accepts jobs posted within the last **48 hours**
(covers both scrape windows). `supervised=true` runs portal fill in the background worker;
`supervised=false` tracks applications without opening browser windows from the API response
(`openUrls` is typically empty in the current UI policy).

## Multi-resume CV library
Each uploaded CV stores an isolated `profileSnapshot`. Activating a resume restores that
snapshot into the working profile and search config without mixing other CVs.

## Auth
Most endpoints require a Bearer token from `POST /api/auth/login`.
""".strip()

OPENAPI_TAGS = [
    {
        "name": "Health",
        "description": "Service health and readiness probes.",
    },
    {
        "name": "Auth",
        "description": "Login, registration, session, and current-user endpoints.",
    },
    {
        "name": "User",
        "description": "Account profile, password, and notification preferences.",
    },
    {
        "name": "Notifications",
        "description": "Notification setup, history, and delivery tests.",
    },
    {
        "name": "Overview",
        "description": "Command-center overview metrics.",
    },
    {
        "name": "Campaigns",
        "description": "Campaign studio workspace, drafts, SMTP, and contact lists.",
    },
    {
        "name": "Job Automation",
        "description": (
            "Recruiting automation: multi-resume profile, portal search, "
            "24h/48h scrape, CV↔JD match routing (≥65% apply / 40–65% tailor / <40% reject), "
            "background apply, CV analyzer, and application tracker."
        ),
    },
    {
        "name": "Day Report",
        "description": "Daily recruiter activity dashboards and filters.",
    },
    {
        "name": "Submissions",
        "description": "Monthly submission progress dashboards.",
    },
    {
        "name": "LinkedIn",
        "description": "LinkedIn recruiter discovery, outreach queue, and sequences.",
    },
    {
        "name": "Meta",
        "description": "API catalog and test-data utilities (admin).",
    },
]
