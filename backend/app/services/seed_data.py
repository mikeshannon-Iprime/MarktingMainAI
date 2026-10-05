from __future__ import annotations

import re
from copy import deepcopy
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union

from app.services.test_data_store import (
    LIST_DATASETS,
    append_test_data as append_rows_to_dataset,
    get_test_data,
    get_test_data_snapshot,
    reset_test_data,
    save_test_data,
)


def _pg_backend():
    from app.core.config import get_settings
    from app.db.database import get_engine

    if get_settings().use_seed_data or get_engine() is None:
        return None
    from app.services import pg_store

    return pg_store


def _data() -> Dict[str, Any]:
    return get_test_data()


_USER_JOB_AUTOMATION: Dict[str, Dict[str, Any]] = {}

_DEFAULT_PORTALS = [
    {"name": "Dice", "url": "https://www.dice.com", "status": "Active"},
    {"name": "Monster", "url": "https://www.monster.com", "status": "Active"},
    {"name": "CareerBuilder", "url": "https://www.careerbuilder.com", "status": "Active"},
]


def _portal_items(payload: Dict[str, Any]) -> List[dict]:
    portals = payload.get("portal_items") or []
    return portals if portals else deepcopy(_DEFAULT_PORTALS)


def _user_job_automation_data(user_external_id: str | None = None) -> Dict[str, Any]:
    data = _data()
    if not user_external_id:
        return data
    if user_external_id not in _USER_JOB_AUTOMATION:
        _USER_JOB_AUTOMATION[user_external_id] = {
            "job_profile": deepcopy(data["job_profile"]),
            "search_config": deepcopy(data["search_config"]),
            "job_automation": deepcopy(data["job_automation"]),
        }
    return _USER_JOB_AUTOMATION[user_external_id]


def _campaign_metrics() -> Dict[str, Union[int, float]]:
    items = _data()["campaign_items"]
    total_sent = sum(item["sent"] for item in items)
    total_opened = sum(item["opened"] for item in items)
    total_replied = sum(item["replied"] for item in items)
    open_rate = 0 if total_sent == 0 else round(total_opened / total_sent * 100)
    reply_rate = 0 if total_sent == 0 else round(total_replied / total_sent * 100)
    return {
        "emailsSent": total_sent,
        "openRate": open_rate,
        "replyRate": reply_rate,
        "bounceRate": 2,
    }


def get_overview_payload(user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.get_overview_payload(user_external_id)
    payload = _data()
    campaign_metrics = _campaign_metrics()
    submission_months = payload["submission_months"]
    job_results = payload["job_results"]
    return {
        "headline": "MarketingMind AI operating system for staffing campaigns, recruiter dashboards, and job automation.",
        "modules": [
            {
                "slug": "campaigns",
                "label": "Campaign Studio",
                "description": "Mass email drafting, templates, contact lists, scheduling, and compliance.",
                "metric": f"{campaign_metrics['emailsSent']:,} sends",
            },
            {
                "slug": "job-automation",
                "label": "Job Automation",
                "description": "Profile setup, search automation, portal management, CV analysis, LinkedIn, and tracker.",
                "metric": f"{len(job_results)} high-match roles",
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
                "metric": f"{submission_months[-1]['submissions']} this month",
            },
        ],
        "activity": [
            {"title": "Campaign queue ready", "detail": "Data/AI Bench Update is scheduled for 08:45 with smart throttling enabled."},
            {"title": "Recruiter output rising", "detail": "Komal leads sourced volume this week with 18 qualified profiles."},
            {"title": "Action required", "detail": "One AI/ML application needs a tailored resume before submission."},
        ],
    }


def get_campaign_workspace(user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.get_campaign_workspace(user_external_id)
    payload = _data()
    return {
        "metrics": _campaign_metrics(),
        "composer": {
            "campaignName": "May Talent Pulse - Southwest",
            "fromName": "Sarah Mitchell",
            "fromEmail": "sarah@marketingmind.ai",
            "replyTo": "recruiter@marketingmind.ai",
            "subject": "Available consultants | {{candidate_name}} | {{location}} | C2C",
            "body": payload["campaign_templates"][0]["body"],
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
                "Rate negotiation",
                "Availability update",
            ],
        },
        "contacts": payload["campaign_contacts"],
        "lists": payload["campaign_lists"],
        "campaigns": payload["campaign_items"],
        "templates": payload["campaign_templates"],
        "settings": deepcopy(payload["campaign_settings"]),
    }


def _is_interview_status(status: str | None) -> bool:
    return str(status or "").strip().lower() in {"interview", "offer"}


def _is_action_needed_status(status: str | None) -> bool:
    normalized = str(status or "").strip().lower()
    return normalized in {"action needed", "tailoring", "failed"}


def _is_submitted_status(status: str | None) -> bool:
    normalized = str(status or "").strip().lower()
    return normalized in {"applied", "interview", "offer", "applying"}


def partition_applications(applications: List[dict]) -> dict:
    """Split tracker rows into interviews / action-needed buckets."""
    interviews = [item for item in applications if _is_interview_status(item.get("status"))]
    action_needed = [item for item in applications if _is_action_needed_status(item.get("status"))]
    return {
        "all": list(applications),
        "interviews": interviews,
        "actionNeeded": action_needed,
    }


def _compute_application_stats(applications: List[dict], job_results: List[dict]) -> dict:
    interviews = [item for item in applications if _is_interview_status(item.get("status"))]
    action_needed = [item for item in applications if _is_action_needed_status(item.get("status"))]
    submitted = [item for item in applications if _is_submitted_status(item.get("status"))]
    under_review = [
        item for item in applications
        if str(item.get("status") or "").strip().lower() == "applied"
    ]
    match_values = [item["match"] for item in applications if item.get("match") is not None]
    if match_values:
        avg_match = round(sum(match_values) / len(match_values))
    elif job_results:
        avg_match = round(sum(job["match"] for job in job_results) / max(len(job_results), 1))
    else:
        avg_match = 0
    portal_counts: dict[str, int] = {}
    for item in applications:
        portal = item.get("portal") or "Direct"
        portal_counts[portal] = portal_counts.get(portal, 0) + 1
    best_platform = max(portal_counts, key=portal_counts.get) if portal_counts else "—"
    response_rate = round((len(interviews) / len(submitted)) * 100) if submitted else 0

    # Estimate average response time from application date → interview/update when possible.
    day_gaps: List[int] = []
    for item in interviews:
        start = str(item.get("date") or "").strip()[:10]
        end = str(item.get("updated") or "").strip()[:10]
        if len(start) == 10 and len(end) == 10 and start <= end:
            try:
                start_dt = datetime.strptime(start, "%Y-%m-%d").date()
                end_dt = datetime.strptime(end, "%Y-%m-%d").date()
                day_gaps.append(max((end_dt - start_dt).days, 0))
            except ValueError:
                continue
    if day_gaps:
        avg_days = round(sum(day_gaps) / len(day_gaps), 1)
        avg_response_time = f"{avg_days} days"
    else:
        avg_response_time = "—"

    return {
        "applied": len(submitted) if submitted else len(applications),
        "underReview": len(under_review),
        "interviews": len(interviews),
        "actionNeeded": len(action_needed),
        "conversion": response_rate,
        "responseRate": response_rate,
        "avgMatchScore": avg_match,
        "avgResponseTime": avg_response_time,
        "bestPlatform": best_platform,
        "totalTracked": len(applications),
    }


def build_applications_payload(applications: List[dict], job_results: Optional[List[dict]] = None) -> dict:
    partitioned = partition_applications(applications)
    return {
        **partitioned,
        "stats": _compute_application_stats(applications, job_results or []),
    }


def get_job_automation_workspace(user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.get_job_automation_workspace(user_external_id)
    payload = _data()
    user_data = _user_job_automation_data(user_external_id)
    applications = payload["applications"]
    job_results = payload["job_results"]
    applications_payload = build_applications_payload(applications, job_results)
    interviews = applications_payload["interviews"]
    return {
        "stats": {
            "appliedToday": 6,
            "newMatches": len(job_results),
            "interviews": len(interviews),
            "avgMatchScore": round(sum(job["match"] for job in job_results) / len(job_results)) if job_results else 0,
        },
        "profile": deepcopy(user_data["job_profile"]),
        "automation": deepcopy(user_data["job_automation"]),
        "search": deepcopy(user_data["search_config"]),
        "resumes": deepcopy(user_data.get("resumes", [])),
        "portals": deepcopy(_portal_items(payload)),
        "carriers": deepcopy(payload["carrier_items"]),
        "results": job_results,
        "savedJobs": deepcopy(payload.get("saved_jobs", [])),
        "analysis": {
            "selectedJobId": 1,
            "score": 87,
            "summary": "Strong fit for backend and cloud-heavy roles with room to sharpen leadership positioning.",
            "hits": ["Java", "Spring Boot", "AWS", "REST APIs", "Microservices"],
            "misses": ["Kubernetes", "GraphQL"],
            "suggestions": [
                "Move recent Spring Boot architecture work into the top summary section.",
                "Add measurable AWS migration outcomes to the first project entry.",
                "Highlight mentoring and ownership for senior-level screening.",
            ],
        },
        "linkedin": payload["linkedin_jobs"],
        "applications": applications_payload,
    }


def get_day_report_dashboard() -> dict:
    backend = _pg_backend()
    if backend:
        return backend.get_day_report_dashboard()
    from app.services.reporting_helpers import day_report_bounds_and_defaults

    rows = _data()["day_report_rows"]
    totals = {
        "linkedin": sum(row.get("linkedin") or 0 for row in rows),
        "calls": sum(row.get("calls") or 0 for row in rows),
        "sourced": sum(row.get("sourced") or 0 for row in rows),
        "marketing": sum(row.get("marketing") or 0 for row in rows),
    }
    meta = day_report_bounds_and_defaults([row["date"] for row in rows])
    return {
        "range": {"start": rows[0]["date"], "end": rows[-1]["date"]},
        **meta,
        "recruiters": sorted({row["recruiter"] for row in rows}),
        "totals": totals,
        "rows": rows,
    }


def get_submission_dashboard() -> dict:
    backend = _pg_backend()
    if backend:
        return backend.get_submission_dashboard()
    from app.services.reporting_helpers import submission_summary

    months = _data()["submission_months"]
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
        "range": {"start": months[0]["month"], "end": months[-1]["month"]},
        "summary": submission_summary(enriched),
        "months": enriched,
    }


def preview_campaign(subject: str, body: str, recipients: List[str], user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.preview_campaign(subject, body, recipients, user_external_id)
    from app.services.campaign_email import build_preview

    data = _data()
    settings = data.get("campaign_settings", {})
    composer = data.get("campaign_composer") or {}
    contacts = data.get("campaign_contacts", [])
    return build_preview(subject, body, recipients, contacts=contacts, composer=composer, settings=settings)


def preview_template(subject: str, body: str, composer: Optional[dict] = None, user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.preview_template(subject, body, composer, user_external_id)
    from app.services.campaign_email import build_preview

    data = _data()
    settings = data.get("campaign_settings", {})
    workspace_composer = {**(data.get("campaign_composer") or {}), **(composer or {})}
    contacts = data.get("campaign_contacts", [])
    recipients = [contacts[0]["email"]] if contacts else []
    return build_preview(subject, body, recipients, contacts=contacts, composer=workspace_composer, settings=settings)


def send_test_campaign(email: str, subject: str, body: str, composer: Optional[dict] = None, user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.send_test_campaign(email, subject, body, composer, user_external_id)
    from app.services.campaign_email import send_test_email

    data = _data()
    settings = data.get("campaign_settings", {})
    workspace_composer = data.get("campaign_composer") or {}
    merged_composer = {**workspace_composer, **(composer or {})}
    return send_test_email(email, subject, body, settings=settings, composer=merged_composer)


def launch_campaign(payload: dict, user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.launch_campaign(payload, user_external_id)
    from app.services.campaign_email import CampaignEmailError, launch_campaign_batch

    data = _data()
    settings = {**data.get("campaign_settings", {}), "emailDelaySeconds": payload.get("emailDelaySeconds", 3)}
    if payload.get("openTracking") is not None:
        settings["openTracking"] = payload["openTracking"]
    contacts = data.get("campaign_contacts", [])

    try:
        result = launch_campaign_batch(payload, settings=settings, contacts=contacts)
    except CampaignEmailError as exc:
        return {"success": False, "message": str(exc), "mode": "demo", "campaign": None, "sentCount": 0, "failedCount": 0}

    campaign = result.get("campaign") or {}
    data["campaign_items"].insert(
        0,
        {
            "name": campaign.get("name") or payload["campaignName"],
            "sent": campaign.get("sent", 0),
            "opened": campaign.get("opened", 0),
            "replied": campaign.get("replied", 0),
            "status": campaign.get("status") or ("Sent" if payload.get("sendNow") else "Scheduled"),
            "scheduledFor": campaign.get("scheduledFor") or payload.get("scheduledFor"),
            "subject": campaign.get("subject") or payload.get("subject"),
            "body": campaign.get("body") or payload.get("body"),
        },
    )
    save_test_data()
    return {
        "success": result["success"],
        "message": result["message"],
        "mode": result.get("mode", "demo"),
        "campaign": campaign,
        "sentCount": campaign.get("sent", 0),
        "failedCount": len(campaign.get("failures") or []),
    }


def save_campaign_draft(payload: dict, user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.save_campaign_draft(payload, user_external_id)
    data = _data()
    draft = {
        "name": payload["campaignName"],
        "sent": 0,
        "opened": 0,
        "replied": 0,
        "status": "Draft",
        "scheduledFor": "—",
        "subject": payload.get("subject", ""),
        "body": payload.get("body", ""),
    }
    data["campaign_items"] = [
        item for item in data["campaign_items"] if not (item.get("name") == draft["name"] and item.get("status") == "Draft")
    ]
    data["campaign_items"].insert(0, draft)
    save_test_data()
    return {"success": True, "message": f"Draft '{payload['campaignName']}' saved.", "campaign": draft}


def import_campaign_contacts(payload: dict, user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.import_campaign_contacts(payload, user_external_id)
    data = _data()
    list_name = payload.get("listName") or "Imported"
    incoming = payload.get("contacts") or []
    seen = {item["email"].lower() for item in data["campaign_contacts"]}
    imported_rows = []
    skipped = 0

    for row in incoming:
        email = str(row.get("email", "")).strip().lower()
        if not email or email in seen:
            skipped += 1
            continue
        seen.add(email)
        contact = {
            "name": row.get("name") or email.split("@")[0],
            "email": row.get("email"),
            "company": row.get("company") or email.split("@")[1],
            "status": row.get("status") or "Queued",
            "list": row.get("list") or list_name,
        }
        data["campaign_contacts"].insert(0, contact)
        imported_rows.append(contact)

    list_row = next((item for item in data["campaign_lists"] if item["name"] == list_name), None)
    if list_row:
        list_row["contacts"] = list_row.get("contacts", 0) + len(imported_rows)
    else:
        data["campaign_lists"].insert(0, {"name": list_name, "contacts": len(imported_rows), "openRate": 0, "replyRate": 0})

    save_test_data()
    return {"imported": len(imported_rows), "skipped": skipped, "contacts": imported_rows}


def test_campaign_smtp(settings: Optional[dict] = None, user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.test_campaign_smtp(settings, user_external_id)
    from app.services.campaign_email import test_smtp_connection

    data = _data()
    merged = {**data.get("campaign_settings", {}), **(settings or {})}
    return test_smtp_connection(merged)


def save_campaign_settings(payload: dict, user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.save_campaign_settings(payload, user_external_id)
    data = _data()
    data["campaign_settings"].update(payload)
    save_test_data()
    return {
        "success": True,
        "message": "Campaign settings updated in test data.",
    }


def create_contact_list(name: str, user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.create_contact_list(name, user_external_id)
    data = _data()
    new_list = {
        "name": name,
        "contacts": 0,
        "openRate": 0,
        "replyRate": 0,
    }
    data["campaign_lists"].insert(0, new_list)
    save_test_data()
    return new_list


def save_job_profile(payload: dict, user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.save_job_profile(payload, user_external_id)
    data = _user_job_automation_data(user_external_id)
    profile = data["job_profile"]
    search = data["search_config"]
    profile.update(payload)
    if "resumeSkills" in payload and payload["resumeSkills"] is not None:
        profile["resumeSkills"] = payload["resumeSkills"]
        search["requiredSkills"] = list(payload["resumeSkills"])
    if payload.get("jobTitles") is not None:
        search["titles"] = list(payload["jobTitles"])
        profile["jobTitles"] = payload["jobTitles"]

    resumes = data.setdefault("resumes", [])
    active = next((item for item in resumes if item.get("isActive")), None)
    if active:
        snapshot = {
            "name": profile.get("name") or "",
            "email": profile.get("email") or "",
            "phone": profile.get("phone") or "",
            "location": profile.get("location") or "",
            "linkedin": profile.get("linkedin") or "",
            "experience": profile.get("experience") or "",
            "employmentType": profile.get("employmentType") or "",
            "rate": profile.get("rate") or "",
            "visa": profile.get("visa") or "",
            "workMode": profile.get("workMode") or "",
            "jobTitles": list(profile.get("jobTitles") or []),
            "resumeFileName": active.get("fileName"),
            "resumeSummary": profile.get("resumeSummary") or "",
            "resumeSkills": list(profile.get("resumeSkills") or []),
        }
        active["profileSnapshot"] = snapshot
        active["profileName"] = snapshot.get("name") or None
        active["experience"] = snapshot.get("experience") or None
        active["summary"] = snapshot.get("resumeSummary") or ""
        active["skills"] = list(snapshot.get("resumeSkills") or [])
        active["jobTitles"] = list(snapshot.get("jobTitles") or [])
        profile["resumeFileName"] = active.get("fileName")

    if not user_external_id:
        save_test_data()
    return {
        "success": True,
        "message": "Job profile updated in test data.",
        "profile": deepcopy(profile),
        "search": deepcopy(search),
        "resumes": deepcopy(resumes),
    }


def save_automation_settings(payload: dict, user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.save_automation_settings(payload, user_external_id)
    data = _user_job_automation_data(user_external_id)
    automation = data["job_automation"]
    automation.update(payload)
    if not user_external_id:
        save_test_data()
    return {
        "success": True,
        "message": "Automation settings saved.",
        "automation": deepcopy(automation),
    }


def _normalize_employment_category(value: str | None) -> str:
    lowered = str(value or "").strip().lower()
    if not lowered or lowered in ("both", "all", "any") or "both" in lowered:
        return "both"
    if "c2h" in lowered or "contract to hire" in lowered or "contract-to-hire" in lowered:
        return "c2h"
    if "c2c" in lowered or "corp to corp" in lowered:
        return "c2c"
    if "w2" in lowered or "w-2" in lowered:
        return "w2"
    if "full" in lowered and ("time" in lowered or lowered in {"full", "fulltime", "full-time"}):
        return "full_time"
    if lowered in {"full", "fulltime", "full-time"}:
        return "full_time"
    if "contract" in lowered:
        return "contract"
    return lowered


def _employment_matches(job_type: str, employment_filter: str) -> bool:
    if not employment_filter:
        return True
    selected = _normalize_employment_category(employment_filter)
    job = _normalize_employment_category(job_type)
    if selected == "both":
        return True
    if selected == "contract":
        return job in {"contract", "c2c", "w2", "c2h"}
    return selected == job


def _years_to_experience_label(years: Optional[float]) -> Optional[str]:
    if years is None:
        return None
    if years < 3:
        return "1-2 Years"
    if years < 5:
        return "3-5 Years"
    if years < 8:
        return "5-8 Years"
    if years < 12:
        return "8-12 Years"
    return "12+ Years"


def save_search_config(payload: dict, user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.save_search_config(payload, user_external_id)
    data = _user_job_automation_data(user_external_id)
    search = data["search_config"]
    allowed_keys = (
        "titles",
        "requiredSkills",
        "optionalSkills",
        "location",
        "radius",
        "filters",
        "excludeKeywords",
        "employmentType",
        "minMatchScore",
        "postedWithin",
        "experienceLevel",
        "rateMin",
        "rateMax",
        "repeatEvery",
    )
    for key in allowed_keys:
        if key in payload and payload[key] is not None:
            search[key] = payload[key]
    if not user_external_id:
        save_test_data()
    return {
        "success": True,
        "message": "Search configuration saved.",
        "search": deepcopy(search),
    }


def apply_parsed_resume(
    parsed: dict,
    filename: str,
    user_external_id: str | None = None,
    assessment: dict | None = None,
    file_bytes: bytes | None = None,
    content_type: str | None = None,
) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.apply_parsed_resume(
            parsed,
            filename,
            user_external_id,
            assessment,
            file_bytes=file_bytes,
            content_type=content_type,
        )
    data = _user_job_automation_data(user_external_id)
    profile = data["job_profile"]
    search = data["search_config"]

    skills = list(parsed.get("skills") or [])
    titles = list(parsed.get("jobTitles") or [])
    experience_label = _years_to_experience_label(parsed.get("yearsExperience"))
    summary = parsed.get("summary") or ""

    snapshot = {
        "name": parsed.get("fullName") or profile.get("name") or "",
        "email": parsed.get("email") or profile.get("email") or "",
        "phone": parsed.get("phone") or profile.get("phone") or "",
        "location": parsed.get("location") or profile.get("location") or "",
        "linkedin": parsed.get("linkedin") or profile.get("linkedin") or "",
        "experience": experience_label or profile.get("experience") or "",
        "employmentType": profile.get("employmentType") or "",
        "rate": profile.get("rate") or "",
        "visa": profile.get("visa") or "",
        "workMode": profile.get("workMode") or "",
        "jobTitles": titles,
        "resumeFileName": filename,
        "resumeSummary": summary,
        "resumeSkills": skills,
    }

    # Replace active working copy from this CV only (no cross-resume merge).
    profile["name"] = snapshot["name"] or profile.get("name")
    profile["email"] = snapshot["email"] or profile.get("email")
    profile["phone"] = snapshot["phone"] or profile.get("phone")
    profile["location"] = snapshot["location"] or profile.get("location")
    if snapshot.get("linkedin"):
        profile["linkedin"] = snapshot["linkedin"]
    if snapshot["experience"]:
        profile["experience"] = snapshot["experience"]
    profile["jobTitles"] = titles
    profile["resumeSkills"] = skills
    profile["resumeFileName"] = filename
    profile["resumeSummary"] = summary
    if titles:
        search["titles"] = titles
    if skills:
        search["requiredSkills"] = skills

    resumes = data.setdefault("resumes", [])
    for item in resumes:
        item["isActive"] = False
    existing = next((item for item in resumes if item["fileName"] == filename), None)
    if not existing:
        existing = {"id": (max((item["id"] for item in resumes), default=0) + 1), "fileName": filename}
        resumes.append(existing)
    existing.update(
        {
            "summary": summary,
            "skills": skills,
            "jobTitles": titles,
            "mlScore": (assessment or {}).get("matchScore"),
            "matchedSkills": (assessment or {}).get("matchedSkills") or [],
            "missingSkills": (assessment or {}).get("missingSkills") or [],
            "isActive": True,
            "uploadedAt": datetime.utcnow().isoformat() + "Z",
            "profileSnapshot": snapshot,
            "profileName": snapshot.get("name") or None,
            "experience": snapshot.get("experience") or None,
            "contentType": content_type,
            "hasFile": bool(file_bytes),
        }
    )

    if not user_external_id:
        save_test_data()
    return {
        "profile": deepcopy(profile),
        "search": deepcopy(search),
        "resumes": deepcopy(resumes),
    }


def list_user_resumes(user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.list_user_resumes(user_external_id)
    data = _user_job_automation_data(user_external_id)
    return {"resumes": deepcopy(data.get("resumes", []))}


def activate_user_resume(resume_id: int, user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.activate_user_resume(resume_id, user_external_id)
    data = _user_job_automation_data(user_external_id)
    resumes = data.setdefault("resumes", [])
    target = next((item for item in resumes if item["id"] == resume_id), None)
    if not target:
        raise ValueError("Resume not found for this user.")
    for item in resumes:
        item["isActive"] = item["id"] == resume_id

    profile = data["job_profile"]
    search = data["search_config"]
    snapshot = dict(target.get("profileSnapshot") or {})
    if not snapshot:
        snapshot = {
            "name": profile.get("name") or "",
            "email": profile.get("email") or "",
            "phone": profile.get("phone") or "",
            "location": profile.get("location") or "",
            "linkedin": profile.get("linkedin") or "",
            "experience": profile.get("experience") or "",
            "employmentType": profile.get("employmentType") or "",
            "rate": profile.get("rate") or "",
            "visa": profile.get("visa") or "",
            "workMode": profile.get("workMode") or "",
            "jobTitles": list(target.get("jobTitles") or []),
            "resumeFileName": target.get("fileName"),
            "resumeSummary": target.get("summary") or "",
            "resumeSkills": list(target.get("skills") or []),
        }
        target["profileSnapshot"] = snapshot
    if not snapshot.get("resumeSkills") and target.get("skills"):
        snapshot["resumeSkills"] = list(target["skills"])
    if not snapshot.get("jobTitles") and target.get("jobTitles"):
        snapshot["jobTitles"] = list(target["jobTitles"])
    if not snapshot.get("resumeSummary") and target.get("summary"):
        snapshot["resumeSummary"] = target["summary"]
    snapshot["resumeFileName"] = target["fileName"]

    for key in (
        "name",
        "email",
        "phone",
        "location",
        "linkedin",
        "experience",
        "employmentType",
        "rate",
        "visa",
        "workMode",
    ):
        if snapshot.get(key):
            profile[key] = snapshot[key]
    profile["jobTitles"] = list(snapshot.get("jobTitles") or [])
    profile["resumeSkills"] = list(snapshot.get("resumeSkills") or [])
    profile["resumeSummary"] = snapshot.get("resumeSummary") or ""
    profile["resumeFileName"] = target["fileName"]
    if snapshot.get("jobTitles"):
        search["titles"] = list(snapshot["jobTitles"])
    if snapshot.get("resumeSkills"):
        search["requiredSkills"] = list(snapshot["resumeSkills"])

    return {
        "success": True,
        "message": f"{target['fileName']} is now the active CV.",
        "resumes": deepcopy(resumes),
        "profile": deepcopy(profile),
        "search": deepcopy(search),
    }


def delete_user_resume(resume_id: int, user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.delete_user_resume(resume_id, user_external_id)
    data = _user_job_automation_data(user_external_id)
    resumes = data.setdefault("resumes", [])
    target = next((item for item in resumes if item["id"] == resume_id), None)
    if not target:
        raise ValueError("Resume not found for this user.")
    was_active = bool(target.get("isActive"))
    resumes.remove(target)
    profile = data["job_profile"]
    search = data["search_config"]
    if was_active and resumes:
        fallback = resumes[-1]
        fallback["isActive"] = True
        # Reuse activate semantics via snapshot hydration.
        activated = activate_user_resume(fallback["id"], user_external_id)
        return {
            "success": True,
            "message": f"{target['fileName']} removed from your CV library.",
            "resumes": activated["resumes"],
            "profile": activated["profile"],
            "search": activated.get("search", deepcopy(search)),
        }
    if was_active:
        profile["resumeFileName"] = None
        profile["resumeSummary"] = None
        profile["resumeSkills"] = []
        profile["jobTitles"] = []
    return {
        "success": True,
        "message": f"{target['fileName']} removed from your CV library.",
        "resumes": deepcopy(resumes),
        "profile": deepcopy(profile),
        "search": deepcopy(search),
    }


def _parse_rate_value(rate_label: str) -> Optional[int]:
    if not rate_label:
        return None
    match = re.search(r"\d[\d,]*", str(rate_label))
    if not match:
        return None
    return int(match.group(0).replace(",", ""))


def _posted_within_days(posted_label: str) -> int:
    numeric = re.search(r"\d+", str(posted_label))
    return int(numeric.group(0)) if numeric else 999


def _posted_within_24_hours(posted_label: str) -> bool:
    """Eligible apply window: posts within the last 48 hours (covers 24h + 48h scrapes)."""
    label = str(posted_label or "").strip().lower()
    if not label:
        return False
    numeric = re.search(r"\d+", label)
    if not numeric:
        return False
    value = int(numeric.group(0))
    if "hour" in label or "hr" in label or "h " in f"{label} ":
        return value <= 48
    if "day" in label or "d " in f"{label} ":
        return value <= 2
    # Plain numeric labels are treated as days in seed data.
    return value <= 2


def _experience_matches(job: dict, experience_filter: str) -> bool:
    if not experience_filter or experience_filter.lower() == "any":
        return True
    role = job.get("role", "").lower()
    if "lead" in experience_filter.lower() or "principal" in experience_filter.lower():
        return any(token in role for token in ("lead", "principal", "architect", "staff"))
    if "senior" in experience_filter.lower():
        return "senior" in role or "lead" in role
    if "mid" in experience_filter.lower():
        return any(token in role for token in ("developer", "engineer", "analyst"))
    return True


def run_job_search(payload: dict, user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.run_job_search(payload, user_external_id)
    data = _data()
    data["search_config"].update({key: value for key, value in payload.items() if value is not None})
    profile = data.get("job_profile", {})
    portals = data.get("portal_items", [])
    titles = payload.get("titles") or data["search_config"].get("titles") or profile.get("jobTitles") or []
    required_skills = [skill.lower() for skill in payload.get("requiredSkills", data["search_config"].get("requiredSkills", []))]
    optional_skills = [skill.lower() for skill in payload.get("optionalSkills", data["search_config"].get("optionalSkills", []))]
    min_score = int(payload.get("minMatchScore", data["search_config"].get("minMatchScore", 70)))
    employment_type = payload.get("employmentType", data["search_config"].get("employmentType", "Both"))
    exclude_keywords = [kw.lower() for kw in payload.get("excludeKeywords", [])]
    raw_posted_within = int(payload.get("postedWithin") or data["search_config"].get("postedWithin") or 2)
    posted_within = min(max(raw_posted_within, 1), 2)
    experience_level = payload.get("experienceLevel") or data["search_config"].get("experienceLevel", "Any")
    rate_min = _parse_rate_value(payload.get("rateMin") or data["search_config"].get("rateMin", ""))
    rate_max = _parse_rate_value(payload.get("rateMax") or data["search_config"].get("rateMax", ""))

    from app.services.portal_scraper import scrape_all_portal_jobs
    from app.services.job_match_ai import enrich_and_rank_jobs

    next_id = max((job.get("id", 0) for job in data["job_results"]), default=0) + 1
    scraped_jobs, _ = scrape_all_portal_jobs(
        portals,
        titles=titles,
        skills=profile.get("resumeSkills", []),
        required_skills=required_skills,
        location=payload.get("location") or data["search_config"].get("location") or profile.get("location", "Remote"),
        existing_jobs=data["job_results"],
        next_job_id=next_id,
        posted_within=str(posted_within),
    )
    if scraped_jobs:
        data["job_results"].extend(scraped_jobs)

    prefiltered = []

    for job in data["job_results"]:
        role_text = job["role"].lower()
        if titles and not any(title.lower() in role_text for title in titles):
            continue
        if not _employment_matches(job.get("type", ""), employment_type):
            continue
        if _posted_within_days(job.get("posted", "999")) > posted_within:
            continue
        if not _posted_within_24_hours(job.get("posted", "")):
            continue
        if not _experience_matches(job, experience_level):
            continue
        job_rate = _parse_rate_value(job.get("rate", ""))
        if rate_min is not None and job_rate is not None and job_rate < rate_min:
            continue
        if rate_max is not None and job_rate is not None and job_rate > rate_max:
            continue
        job_blob = " ".join(
            [
                job["role"],
                job["company"],
                job["location"],
                job.get("description", ""),
                " ".join(job.get("skills", [])),
            ]
        ).lower()
        if exclude_keywords and any(kw in job_blob for kw in exclude_keywords if kw):
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
        prefiltered.append(enriched)

    if not prefiltered and data["job_results"]:
        prefiltered = [dict(job) for job in data["job_results"][:50]]

    profile = data.get("job_profile", {})
    ranked, matching_pipeline = enrich_and_rank_jobs(prefiltered, profile, data["search_config"])
    filtered = [job for job in ranked if job.get("match", 0) >= min_score]
    if not filtered and ranked:
        filtered = ranked[: min(20, len(ranked))]
        matching_pipeline = {
            **matching_pipeline,
            "message": (
                f"{matching_pipeline.get('message', '')} "
                f"Showing top {len(filtered)} embedding-ranked matches below {min_score}% threshold."
            ).strip(),
        }
    ranked = filtered

    save_test_data()
    portal_names = ", ".join({p["name"] for p in portals}) if portals else "configured sources"
    scrape_note = f" Scraped {len(scraped_jobs)} new posting(s) across {len(portals)} portal(s)." if portals else ""
    return {
        "success": True,
        "message": f"Search completed across {portal_names} with {len(ranked)} matching jobs (min {min_score}%).{scrape_note} {matching_pipeline['message']}",
        "results": ranked,
        "scrapedCount": len(scraped_jobs),
        "portalsScraped": len(portals),
        "matchingPipeline": matching_pipeline,
    }


def save_job(job_id: int) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.save_job(job_id)
    data = _data()
    saved = data.setdefault("saved_jobs", [])
    if job_id in saved:
        saved.remove(job_id)
        save_test_data()
        return {"success": True, "message": "Job removed from saved list.", "saved": False}
    saved.append(job_id)
    save_test_data()
    return {"success": True, "message": "Job saved to favorites.", "saved": True}


def add_portal(name: str, url: str) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.add_portal(name, url)
    data = _data()
    portal = {"name": name, "url": url, "status": "Active"}
    data["portal_items"].append(portal)
    save_test_data()
    return {"success": True, "message": f"Portal '{name}' added.", "portal": portal}


def add_carrier(name: str, url: str) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.add_carrier(name, url)
    data = _data()
    carrier = {"name": name, "url": url, "status": "Monitoring"}
    data["carrier_items"].append(carrier)
    save_test_data()
    return {"success": True, "message": f"Carrier '{name}' added.", "carrier": carrier}


def delete_portal(name: str, url: str) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.delete_portal(name, url)
    data = _data()
    before = len(data["portal_items"])
    data["portal_items"] = [p for p in data["portal_items"] if not (p["name"] == name and p["url"] == url)]
    if len(data["portal_items"]) == before:
        raise ValueError(f"Portal '{name}' not found.")
    save_test_data()
    return {"success": True, "message": f"Portal '{name}' removed."}


def delete_carrier(name: str, url: str) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.delete_carrier(name, url)
    data = _data()
    before = len(data["carrier_items"])
    data["carrier_items"] = [c for c in data["carrier_items"] if not (c["name"] == name and c["url"] == url)]
    if len(data["carrier_items"]) == before:
        raise ValueError(f"Carrier '{name}' not found.")
    save_test_data()
    return {"success": True, "message": f"Carrier '{name}' removed."}


def import_portals(portals: List[dict]) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.import_portals(portals)
    data = _data()
    added = 0
    for item in portals:
        portal = {"name": item["name"], "url": item["url"], "status": "Active"}
        if not any(p["url"] == portal["url"] for p in data["portal_items"]):
            data["portal_items"].append(portal)
            added += 1
    save_test_data()
    return {"success": True, "message": f"Imported {added} portal(s).", "portals": deepcopy(data["portal_items"])}


def import_carriers(carriers: List[dict]) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.import_carriers(carriers)
    data = _data()
    added = 0
    for item in carriers:
        carrier = {
            "name": item["name"],
            "url": item["url"],
            "status": item.get("status") or "Monitoring",
        }
        if not any(c["url"] == carrier["url"] for c in data["carrier_items"]):
            data["carrier_items"].append(carrier)
            added += 1
    save_test_data()
    return {"success": True, "message": f"Imported {added} carrier page(s).", "carriers": deepcopy(data["carrier_items"])}


def apply_jobs(
    job_ids: List[int],
    user_external_id: str | None = None,
    supervised: bool = True,
    use_tailored_resume: bool = True,
) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.apply_jobs(
            job_ids,
            user_external_id,
            supervised=supervised,
            use_tailored_resume=use_tailored_resume,
        )
    data = _data()
    selected_jobs = [job for job in data["job_results"] if job["id"] in job_ids]
    eligible_jobs = [job for job in selected_jobs if _posted_within_24_hours(job.get("posted", ""))]
    skipped = len(selected_jobs) - len(eligible_jobs)
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
    applications = []
    for job in eligible_jobs:
        row = {
            "id": len(data["applications"]) + 1,
            "jobResultId": job["id"],
            "role": job["role"],
            "company": job["company"],
            "status": "Applied",
            "stage": "Application submitted from test endpoint",
            "updated": date.today().isoformat(),
            "date": date.today().isoformat(),
            "action": "Await recruiter response",
            "portal": job.get("portalName") or "Direct",
            "match": job.get("match"),
            "postingUrl": job.get("sourceUrl") or job.get("portalUrl") or "",
            "attemptStatus": "demo" if supervised else "manual",
            "attemptDetail": "Seed-data apply (no live portal).",
            "confirmationUrl": job.get("sourceUrl") or job.get("portalUrl") or "",
        }
        data["applications"].insert(0, row)
        applications.append(row)
    save_test_data()
    return {
        "success": True,
        "message": (
            f"Applied to {len(eligible_jobs)} job(s) using test data."
            + (f" Skipped {skipped} job(s) older than 48 hours." if skipped else "")
        ),
        "applied": len(eligible_jobs),
        "applications": applications,
        "openUrls": [],
        "supervised": False,
        "tailoredJobIds": [],
    }


def get_job_application(application_id: int, user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.get_job_application(application_id, user_external_id)
    data = _data()
    for row in data.get("applications") or []:
        if row.get("id") == application_id:
            return deepcopy(row)
    raise ValueError("Application not found.")


def list_recent_job_applications(user_external_id: str | None = None, limit: int = 20) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.list_recent_job_applications(user_external_id, limit=limit)
    data = _data()
    rows = list(data.get("applications") or [])[: max(1, min(limit, 200))]
    payload = build_applications_payload(rows, data.get("job_results") or [])
    return {"applications": deepcopy(rows), "tracker": payload}


def update_job_application(
    application_id: int,
    *,
    status: Optional[str] = None,
    stage: Optional[str] = None,
    action: Optional[str] = None,
    notes: Optional[str] = None,
    user_external_id: str | None = None,
) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.update_job_application(
            application_id,
            status=status,
            stage=stage,
            action=action,
            notes=notes,
            user_external_id=user_external_id,
        )
    data = _data()
    row = next((item for item in data.get("applications") or [] if item.get("id") == application_id), None)
    if not row:
        raise ValueError("Application not found.")
    allowed = {
        "Applying", "Applied", "Action Needed", "Interview", "Offer", "Tailoring", "Rejected", "Failed",
    }
    if status is not None:
        cleaned = str(status).strip()
        if cleaned not in allowed:
            raise ValueError(f"Unsupported status '{cleaned}'.")
        row["status"] = cleaned
    if stage is not None and str(stage).strip():
        row["stage"] = str(stage).strip()
    if action is not None and str(action).strip():
        row["action"] = str(action).strip()
    if notes is not None and str(notes).strip():
        existing = str(row.get("attemptDetail") or "").strip()
        detail = str(notes).strip()
        row["attemptDetail"] = f"{existing}\n{detail}".strip() if existing else detail
    row["updated"] = date.today().isoformat()
    save_test_data()
    return {"success": True, "message": f"Application updated to {row['status']}.", "application": deepcopy(row)}


def schedule_application_followup(
    application_id: int,
    *,
    note: Optional[str] = None,
    user_external_id: str | None = None,
) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.schedule_application_followup(
            application_id,
            note=note,
            user_external_id=user_external_id,
        )
    data = _data()
    row = next((item for item in data.get("applications") or [] if item.get("id") == application_id), None)
    if not row:
        raise ValueError("Application not found.")
    follow_date = date.today().isoformat()
    detail = note.strip() if note and note.strip() else "Follow-up reminder scheduled from Tracker."
    row["action"] = f"Follow-up scheduled ({follow_date})"
    row["stage"] = "Awaiting recruiter reply"
    if row.get("status") in {"Applied", "Applying", "Failed"}:
        row["status"] = "Action Needed"
    existing = str(row.get("attemptDetail") or "").strip()
    stamp = f"[{follow_date}] {detail}"
    row["attemptDetail"] = f"{existing}\n{stamp}".strip() if existing else stamp
    row["updated"] = follow_date
    save_test_data()
    return {
        "success": True,
        "message": f"Follow-up scheduled for {row.get('role')} at {row.get('company')}.",
        "application": deepcopy(row),
    }

def analyze_job(
    job_id: Optional[int] = None,
    job_description: Optional[str] = None,
    user_external_id: str | None = None,
) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.analyze_job(
            job_id=job_id,
            job_description=job_description,
            user_external_id=user_external_id,
        )
    from app.services.analyzer_service import build_match_analysis

    data = _data()
    user_data = _user_job_automation_data(user_external_id)
    jobs = data["job_results"]
    selected = next((job for job in jobs if job["id"] == job_id), None) if job_id else None
    return build_match_analysis(
        profile=user_data["job_profile"],
        selected_job=selected,
        job_description=(job_description or "").strip(),
        job_id=job_id,
    )


def refresh_job_description(
    job_id: int,
    user_external_id: str | None = None,
    *,
    force: bool = True,
) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.refresh_job_description(job_id, user_external_id, force=force)
    data = _data()
    selected = next((job for job in data["job_results"] if job["id"] == job_id), None)
    if not selected:
        raise ValueError("Job not found for this user.")
    return {
        "success": True,
        "jobId": job_id,
        "role": selected.get("role"),
        "company": selected.get("company"),
        "sourceUrl": selected.get("sourceUrl"),
        "description": selected.get("description") or "",
        "descriptionQuality": "summary",
        "fetchedFromPortal": False,
        "message": "Seed mode — returning stored description.",
    }


def re_find_skills(text: str) -> List[str]:
    from app.services.analyzer_service import find_skills_in_text

    return find_skills_in_text(text)


def tailor_resume_for_job(
    job_id: int,
    job_description: Optional[str] = None,
    user_external_id: str | None = None,
) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.tailor_resume_for_job(job_id, job_description, user_external_id)
    from app.services.analyzer_service import build_surgical_tailor

    analysis = analyze_job(
        job_id=job_id,
        job_description=job_description,
        user_external_id=user_external_id,
    )
    data = _data()
    user_data = _user_job_automation_data(user_external_id)
    selected = next((job for job in data["job_results"] if job["id"] == job_id), None)
    if not selected:
        raise ValueError("Job not found for this user.")
    profile = user_data["job_profile"]
    existing = get_tailored_resume(job_id, user_external_id)
    existing_content = existing.get("content") if existing.get("found") else ""
    tailored = build_surgical_tailor(
        profile=profile,
        selected_job=selected,
        analysis=analysis,
        active_resume=None,
        existing_tailored=existing_content or "",
    )
    boosted_score = tailored["tailoredScore"]
    return {
        "success": True,
        "jobId": job_id,
        "message": (
            f"Role-aligned adjustments ready for job #{job_id} — "
            f"base resume preserved (estimated match {boosted_score}%)."
        ),
        "content": tailored["content"],
        "adjustments": tailored.get("adjustments") or [],
        "jdPointers": tailored.get("jdPointers") or [],
        "basePreserved": True,
        "tailoredScore": boosted_score,
        "analysis": {**analysis, "tailoredScore": boosted_score},
    }


def save_tailored_resume(
    job_id: int,
    content: str,
    user_external_id: str | None = None,
) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.save_tailored_resume(job_id, content, user_external_id)
    data = _user_job_automation_data(user_external_id)
    tailored = data.setdefault("tailored_resumes", {})
    tailored[str(job_id)] = {"jobId": job_id, "content": content, "savedAt": datetime.utcnow().isoformat()}
    save_test_data()
    return {"success": True, "message": f"Tailored resume saved for job #{job_id}.", "jobId": job_id}


def get_tailored_resume(job_id: int, user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.get_tailored_resume(job_id, user_external_id)
    data = _user_job_automation_data(user_external_id)
    entry = data.get("tailored_resumes", {}).get(str(job_id))
    if not entry:
        return {"jobId": job_id, "content": "", "found": False}
    return {"jobId": job_id, "content": entry["content"], "found": True}


def preview_application_autofill(
    job_id: Optional[int] = None,
    approved_keys: Optional[List[str]] = None,
    user_external_id: str | None = None,
) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.preview_application_autofill(job_id, approved_keys, user_external_id)
    from app.services.analyzer_service import build_autofill_preview

    data = _data()
    user_data = _user_job_automation_data(user_external_id)
    selected = None
    if job_id:
        selected = next((job for job in data["job_results"] if job["id"] == job_id), None)
        if not selected:
            raise ValueError("Job not found for this user.")
    return build_autofill_preview(
        profile=user_data["job_profile"],
        selected_job=selected,
        approved_keys=approved_keys or [],
    )

def run_auto_apply(match_threshold: Optional[int] = None, user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.run_auto_apply(match_threshold, user_external_id)
    data = _data()
    user_data = _user_job_automation_data(user_external_id)
    portals = _portal_items(data)
    if not data.get("portal_items"):
        data["portal_items"] = deepcopy(portals)

    profile = user_data["job_profile"]
    search_config = user_data["search_config"]
    automation = user_data["job_automation"]
    apply_floor = max(65, int(match_threshold or automation.get("matchThreshold", 65) or 65))
    tailor_floor = 40
    tailor_enabled = bool(automation.get("tailorCv", True))
    max_apps = automation.get("maxApplications", 20)
    if not max_apps or max_apps <= 0:
        max_apps = 20

    from app.services.portal_scraper import scrape_all_portal_jobs
    from app.services.job_match_ai import enrich_and_rank_jobs

    next_id = max((job.get("id", 0) for job in data["job_results"]), default=0) + 1
    scraped_jobs: list[dict] = []
    for window in ("1", "2"):
        batch, _ = scrape_all_portal_jobs(
            portals,
            titles=search_config.get("titles") or profile.get("jobTitles") or ["Software Engineer"],
            skills=profile.get("resumeSkills", []),
            required_skills=search_config.get("requiredSkills", []),
            location=search_config.get("location") or profile.get("location", "Remote"),
            existing_jobs=data["job_results"] + scraped_jobs,
            next_job_id=next_id,
            posted_within=window,
        )
        for job in batch:
            job["id"] = next_id
            next_id += 1
            scraped_jobs.append(job)
    if scraped_jobs:
        data["job_results"].extend(scraped_jobs)

    titles = search_config.get("titles") or profile.get("jobTitles") or []
    required_skills = [skill.lower() for skill in search_config.get("requiredSkills", [])]
    optional_skills = [skill.lower() for skill in search_config.get("optionalSkills", [])]
    employment_type = search_config.get("employmentType", "Both")
    exclude_keywords = [kw.lower() for kw in search_config.get("excludeKeywords", [])]
    posted_within = 2
    experience_level = search_config.get("experienceLevel", "Any")
    rate_min = _parse_rate_value(search_config.get("rateMin", ""))
    rate_max = _parse_rate_value(search_config.get("rateMax", ""))

    prefiltered = []
    for job in data["job_results"]:
        role_text = job["role"].lower()
        if titles and not any(title.lower() in role_text for title in titles):
            continue
        if not _employment_matches(job.get("type", ""), employment_type):
            continue
        if _posted_within_days(job.get("posted", "999")) > posted_within:
            continue
        if not _posted_within_24_hours(job.get("posted", "")):
            continue
        if not _experience_matches(job, experience_level):
            continue
        job_rate = _parse_rate_value(job.get("rate", ""))
        if rate_min is not None and job_rate is not None and job_rate < rate_min:
            continue
        if rate_max is not None and job_rate is not None and job_rate > rate_max:
            continue
        job_blob = " ".join(
            [
                job["role"],
                job["company"],
                job["location"],
                job.get("description", ""),
                " ".join(job.get("skills", [])),
            ]
        ).lower()
        if exclude_keywords and any(kw in job_blob for kw in exclude_keywords if kw):
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
        prefiltered.append(enriched)

    if not prefiltered and data["job_results"]:
        prefiltered = [
            dict(job) for job in data["job_results"]
            if _posted_within_24_hours(job.get("posted", ""))
        ][:50]

    all_ranked, matching_pipeline = enrich_and_rank_jobs(prefiltered, profile, search_config)
    ranked = all_ranked
    apply_ids: list[int] = []
    tailor_jobs: list[dict] = []
    reject_jobs: list[dict] = []
    for job in ranked:
        score = int(job.get("match") or 0)
        if score >= apply_floor:
            apply_ids.append(job["id"])
        elif score >= tailor_floor:
            tailor_jobs.append(job)
        else:
            reject_jobs.append(job)

    apply_ids = apply_ids[:max_apps]
    remaining = max(0, max_apps - len(apply_ids))
    tailor_jobs = tailor_jobs[:remaining] if tailor_enabled else []
    reject_jobs = reject_jobs[: max(0, remaining - len(tailor_jobs))]

    tailored_apps = []
    rejected_apps = []
    today = date.today().isoformat()
    for job in tailor_jobs:
        row = {
            "id": len(data["applications"]) + 1,
            "jobResultId": job["id"],
            "role": job["role"],
            "company": job["company"],
            "status": "Tailoring",
            "stage": "CV tailored to job description (40–65% match)",
            "updated": today,
            "date": today,
            "action": "Review tailored CV in Analyzer",
            "portal": job.get("portalName") or "Direct",
            "match": job.get("match"),
            "postingUrl": job.get("sourceUrl") or job.get("portalUrl") or "",
            "attemptStatus": "tailored",
            "attemptDetail": f"Match {job.get('match', 0)}% — CV tailored to JD.",
            "confirmationUrl": "",
        }
        data["applications"].insert(0, row)
        tailored_apps.append(row)
        try:
            tailored = tailor_resume_for_job(job["id"], job.get("description"), user_external_id)
            if tailored.get("content"):
                save_tailored_resume(job["id"], tailored["content"], user_external_id)
        except Exception:
            pass

    for job in reject_jobs:
        row = {
            "id": len(data["applications"]) + 1,
            "jobResultId": job["id"],
            "role": job["role"],
            "company": job["company"],
            "status": "Rejected",
            "stage": "Rejected — CV match below 40%",
            "updated": today,
            "date": today,
            "action": "No action — below match floor",
            "portal": job.get("portalName") or "Direct",
            "match": job.get("match"),
            "postingUrl": job.get("sourceUrl") or job.get("portalUrl") or "",
            "attemptStatus": "rejected",
            "attemptDetail": f"Match {job.get('match', 0)}% is below {tailor_floor}%.",
            "confirmationUrl": "",
        }
        data["applications"].insert(0, row)
        rejected_apps.append(row)

    applied_count = 0
    apply_message = "No jobs met the 65%+ auto-apply threshold."
    if apply_ids:
        result = apply_jobs(apply_ids, user_external_id)
        applied_count = int(result.get("applied") or len(apply_ids))
        apply_message = result.get("message", f"Applied to {applied_count} job(s).")
    save_test_data()
    portal_names = ", ".join({portal["name"] for portal in portals})
    return {
        "success": True,
        "message": (
            f"Scraped {len(scraped_jobs)} posting(s) across {len(portals)} portal(s) ({portal_names}) "
            f"for 24h + 48h. Routed {len(apply_ids)} apply (≥{apply_floor}%), "
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
        "scrapedCount": len(scraped_jobs),
        "portalsScraped": len(portals),
        "postedWindows": ["1", "2"],
        "matchPolicy": {"applyMin": apply_floor, "tailorMin": tailor_floor, "rejectBelow": tailor_floor},
        "matchingPipeline": matching_pipeline,
    }


def search_linkedin_jobs(payload: dict) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.search_linkedin_jobs(payload)
    rows = _data()["linkedin_jobs"]
    query = payload.get("query", "").lower()
    company = payload.get("company", "").lower()
    experience = payload.get("experienceLevel", "all").lower()
    employment = payload.get("employmentType", "all").lower()
    under10 = payload.get("under10Applicants", False)
    date_posted = payload.get("datePosted", "all").lower()
    easy_only = payload.get("easyApplyOnly", False)

    def posted_matches(label: str) -> bool:
        if date_posted == "all":
            return True
        lowered = (label or "").lower()
        if date_posted == "24h":
            return "h ago" in lowered or "hour" in lowered
        if date_posted == "week":
            return "d ago" in lowered or "week" in lowered or "h ago" in lowered
        return True

    filtered = []
    for row in rows:
        haystack = f"{row['role']} {row['company']} {row['location']} {row.get('insight', '')}".lower()
        if query and query not in haystack:
            continue
        if company and company not in row["company"].lower():
            continue
        if experience != "all" and row.get("experienceLevel", "").lower() != experience:
            continue
        if employment != "all":
            row_type = (row.get("type") or "").lower().replace("-", " ")
            employment_norm = employment.lower().replace("-", " ")
            if employment_norm not in row_type and not (employment_norm == "full time" and "full" in row_type):
                continue
        if under10 and row.get("applicants", 99) >= 10:
            continue
        if easy_only and not row.get("easyApply"):
            continue
        if not posted_matches(row.get("posted") or row.get("datePosted", "")):
            continue
        filtered.append(row)

    return {"success": True, "message": f"Found {len(filtered)} LinkedIn roles.", "results": filtered}


def apply_linkedin_job(role: str, company: str, easy_apply: bool) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.apply_linkedin_job(role, company, easy_apply)
    data = _data()
    if easy_apply:
        data["applications"].insert(
            0,
            {
                "role": role,
                "company": company,
                "status": "Applied",
                "stage": "LinkedIn Easy Apply submitted",
                "updated": date.today().isoformat(),
                "action": "Await recruiter response",
            },
        )
        save_test_data()
        return {"success": True, "message": f"Easy Apply submitted for {role} at {company}."}
    return {
        "success": True,
        "message": f"Open LinkedIn to apply for {role} at {company}.",
        "redirect": True,
    }


def filter_day_report(start: Optional[str] = None, end: Optional[str] = None, recruiter: Optional[str] = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.filter_day_report(start, end, recruiter)
    rows = []
    all_rows = _data()["day_report_rows"]
    for row in all_rows:
        if start and row["date"] < start:
            continue
        if end and row["date"] > end:
            continue
        if recruiter and row["recruiter"] != recruiter:
            continue
        rows.append(row)

    totals = {
        "linkedin": sum(row["linkedin"] for row in rows),
        "calls": sum(row["calls"] for row in rows),
        "sourced": sum(row["sourced"] for row in rows),
        "marketing": sum(row["marketing"] for row in rows),
    }
    return {
        "range": {
            "start": start or all_rows[0]["date"],
            "end": end or all_rows[-1]["date"],
        },
        "recruiters": sorted({row["recruiter"] for row in all_rows}),
        "totals": totals,
        "rows": rows,
    }


def filter_submissions(start_month: Optional[str] = None, end_month: Optional[str] = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.filter_submissions(start_month, end_month)
    from app.services.reporting_helpers import submission_summary

    dashboard = get_submission_dashboard()
    months = []
    for month in dashboard["months"]:
        if start_month and month["month"] < start_month:
            continue
        if end_month and month["month"] > end_month:
            continue
        months.append(month)
    return {
        "range": {
            "start": months[0]["month"] if months else start_month or dashboard["range"]["start"],
            "end": months[-1]["month"] if months else end_month or dashboard["range"]["end"],
        },
        "summary": submission_summary(months),
        "months": months,
    }


def get_test_data_payload() -> dict:
    backend = _pg_backend()
    if backend:
        return backend.get_test_data_payload()
    snapshot = get_test_data_snapshot()
    counts = {}
    for key, value in snapshot.items():
        if isinstance(value, list):
            counts[key] = len(value)
    return {
        "dataset": snapshot,
        "counts": counts,
        "appendableDatasets": sorted(LIST_DATASETS),
    }


def append_test_data_payload(dataset: str, entries: List[Dict[str, Any]]) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.append_test_data_payload(dataset, entries)
    total = append_rows_to_dataset(dataset, entries)
    return {
        "success": True,
        "message": f"Appended {len(entries)} record(s) to {dataset}.",
        "dataset": dataset,
        "totalRecords": total,
    }


def reset_test_data_payload() -> dict:
    backend = _pg_backend()
    if backend:
        return backend.reset_test_data_payload()
    reset_test_data()
    return {
        "success": True,
        "message": "Test data reset to baseline JSON.",
    }


_LINKEDIN_RECRUITERS = [
    {"id": 1, "name": "Jessica Turner", "title": "Senior Technical Recruiter", "company": "TEKsystems", "location": "Dallas, TX", "techs": ["Java", "Spring Boot", "AWS"], "conn": "2nd", "avatar": "JT", "match": 96, "source": "Apollo", "email": "j.turner@teksystems.com", "note": "Actively hiring Java developers for Fortune 500 clients", "status": "new"},
    {"id": 2, "name": "Michael Patel", "title": "IT Recruiter — Java & Cloud", "company": "TEKsystems", "location": "Austin, TX", "techs": ["Java", "Microservices", "Kubernetes"], "conn": "1st", "avatar": "MP", "match": 93, "source": "Apollo", "email": "m.patel@teksystems.com", "note": "Specializes in contract C2C placements", "status": "contacted"},
    {"id": 3, "name": "Anita Sharma", "title": "Technical Talent Acquisition", "company": "Infosys BPM", "location": "Remote", "techs": ["Java", "Spring Boot", "DevOps"], "conn": "2nd", "avatar": "AS", "match": 91, "source": "Hunter", "email": "anita.s@infosys.com", "note": "Focuses on backend Java and cloud roles", "status": "new"},
    {"id": 4, "name": "David Rodriguez", "title": "Sr. Recruiter — Software Engineering", "company": "Cognizant", "location": "New York, NY", "techs": ["Java", "React", "AWS"], "conn": "3rd", "avatar": "DR", "match": 88, "source": "Apollo", "email": "d.rodriguez@cognizant.com", "note": "Handles full-stack and Java bench hiring", "status": "new"},
    {"id": 5, "name": "Lisa Chen", "title": "Technology Recruiter", "company": "Capgemini", "location": "Chicago, IL", "techs": ["Java", "Spring", "Hibernate"], "conn": "2nd", "avatar": "LC", "match": 86, "source": "Hunter", "email": "l.chen@capgemini.com", "note": "Mid-to-senior Java developer placements", "status": "replied"},
    {"id": 6, "name": "Kevin Brooks", "title": "Contract Recruiter — Java/Cloud", "company": "HCL Tech", "location": "Remote", "techs": ["Java", "AWS", "Docker"], "conn": "2nd", "avatar": "KB", "match": 84, "source": "Apollo", "email": "k.brooks@hcltech.com", "note": "C2C and W2 contract specialist", "status": "contacted"},
    {"id": 7, "name": "Priya Nair", "title": "Technical Recruiter", "company": "Wipro", "location": "Dallas, TX", "techs": ["Java", "Spring Boot", "SQL"], "conn": "1st", "avatar": "PN", "match": 82, "source": "Apollo", "email": "p.nair@wipro.com", "note": "Active in Texas tech market", "status": "new"},
    {"id": 8, "name": "Robert Kim", "title": "Recruiting Lead — Engineering", "company": "Accenture", "location": "Houston, TX", "techs": ["Java", "Microservices", "Kafka"], "conn": "3rd", "avatar": "RK", "match": 80, "source": "Hunter", "email": "r.kim@accenture.com", "note": "Enterprise Java and integration roles", "status": "new"},
]

_LINKEDIN_SEQUENCES = [
    {"id": 1, "name": "Jessica Turner — TEKsystems", "steps": [{"label": "Connection sent", "status": "sent", "date": "May 5"}, {"label": "Follow-up InMail", "status": "sent", "date": "May 8"}, {"label": "2nd follow-up", "status": "pending", "date": "May 11"}, {"label": "Final touch", "status": "scheduled", "date": "May 14"}]},
    {"id": 2, "name": "Michael Patel — TEKsystems", "steps": [{"label": "Connection sent", "status": "sent", "date": "May 6"}, {"label": "InMail — Java hotlist", "status": "replied", "date": "May 7"}]},
    {"id": 3, "name": "Anita Sharma — Infosys", "steps": [{"label": "InMail sent", "status": "sent", "date": "May 4"}, {"label": "Follow-up", "status": "pending", "date": "May 11"}]},
    {"id": 4, "name": "David Rodriguez — Cognizant", "steps": [{"label": "Connection request", "status": "sent", "date": "May 3"}, {"label": "Follow-up message", "status": "sent", "date": "May 6"}, {"label": "2nd follow-up", "status": "pending", "date": "May 11"}]},
]

_LINKEDIN_FOLLOWUPS = [
    {"name": "Anita Sharma", "company": "Infosys", "due": "Today", "type": "2nd follow-up"},
    {"name": "David Rodriguez", "company": "Cognizant", "due": "Today", "type": "3rd touch"},
    {"name": "Lisa Chen", "company": "Capgemini", "due": "Tomorrow", "type": "InMail follow-up"},
]

_LINKEDIN_TEMPLATES = [
    {"name": "Connection — Java Specialist", "body": "Hi {{recruiter_name}},\n\nI noticed your work at {{company}} and would love to connect. I am a Senior Java/Spring Boot Developer available immediately for C2C roles in {{location}}.\n\nLooking forward to connecting!\n{{candidate_name}}"},
    {"name": "InMail — C2C Hotlist", "body": "Hi {{recruiter_name}},\n\nHope you are doing well! I have a Senior Java Developer with {{tech_stack}} expertise available immediately for C2C contract roles.\n\nWould love to share a full profile if you have any matching requirements.\n\nBest,\n{{candidate_name}}"},
    {"name": "Follow-up — 3 day", "body": "Hi {{recruiter_name}},\n\nFollowing up on my previous message about our Java Developer. This consultant is still available — wanted to check in before the window closes.\n\n{{candidate_name}}"},
]

_LINKEDIN_API_SOURCES = [
    {"id": "apollo", "name": "Apollo.io", "shortCode": "AP", "description": "300M+ contacts · title + email lookup · company search", "status": "connected", "color": "#005f94"},
    {"id": "hunter", "name": "Hunter.io", "shortCode": "HN", "description": "Email finder by name + domain · domain search", "status": "connected", "color": "#92400e"},
    {"id": "rocketreach", "name": "RocketReach", "shortCode": "RR", "description": "Direct dials · LinkedIn URL enrichment", "status": "disconnected", "color": "#5b21b6"},
    {"id": "lusha", "name": "Lusha", "shortCode": "LU", "description": "B2B contact data · phone numbers · company info", "status": "disconnected", "color": "#2e7d32"},
    {"id": "linkedin", "name": "LinkedIn Official API", "shortCode": "LI", "description": "Requires LinkedIn partnership approval · most accurate", "status": "pending", "color": "#0077b5"},
]

_LINKEDIN_SETTINGS = {
    "autoRunDaily": True, "autoEnrich": True, "skipContacted": True, "autoFollowup": True,
    "aiPersonalize": True, "maxPerDay": 25, "delaySeconds": 45,
    "accountEmail": "sarah@techstaff.com", "dailyConnections": 20, "dailyInmails": 10,
    "isPremium": False, "respectDnc": True, "honorUnsubscribes": True, "usePermittedSources": True,
}

_LINKEDIN_API_USAGE = [
    {"label": "Apollo.io lookups", "used": 1240, "limit": 5000},
    {"label": "Hunter.io searches", "used": 340, "limit": 1000},
    {"label": "Emails found", "used": 247, "limit": None},
    {"label": "Credits remaining", "used": 3760, "limit": None},
]
_LINKEDIN_SCHEDULED_OUTREACH: List[Dict[str, Any]] = []


def get_linkedin_workspace(user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.get_linkedin_workspace(user_external_id)
    contacted = sum(1 for r in _LINKEDIN_RECRUITERS if r["status"] in ("contacted", "replied"))
    replied = sum(1 for r in _LINKEDIN_RECRUITERS if r["status"] == "replied")

    # Extract unique companies and technologies from recruiters
    companies = sorted(set(r["company"] for r in _LINKEDIN_RECRUITERS))
    all_techs = set()
    for r in _LINKEDIN_RECRUITERS:
        all_techs.update(r.get("techs", []))
    technologies = sorted(list(all_techs))

    # Get connected APIs
    api_connected = any(s["status"] == "connected" for s in _LINKEDIN_API_SOURCES)

    return {
        "stats": {
            "recruitersFound": len(_LINKEDIN_RECRUITERS),
            "contacted": contacted,
            "replied": replied,
            "followupsDue": len(_LINKEDIN_FOLLOWUPS),
        },
        "recruiters": deepcopy(_LINKEDIN_RECRUITERS),
        "sequences": deepcopy(_LINKEDIN_SEQUENCES),
        "followups": deepcopy(_LINKEDIN_FOLLOWUPS),
        "templates": deepcopy(_LINKEDIN_TEMPLATES),
        "apiSources": deepcopy(_LINKEDIN_API_SOURCES),
        "companies": companies,
        "technologies": technologies,
        "apiConnected": api_connected,
        "pasteProfilesEnabled": True,
        "outreachEnabled": True,
        "apiUsage": deepcopy(_LINKEDIN_API_USAGE),
        "settings": deepcopy(_LINKEDIN_SETTINGS),
    }


def run_linkedin_discovery(companies: list, technologies: list, seniority: str, location: str, connections: str, results_per_company: int, user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.run_linkedin_discovery(companies, technologies, seniority, location, connections, results_per_company, user_external_id)
    filtered = [
        r for r in _LINKEDIN_RECRUITERS
        if (not companies or r["company"] in companies)
        and (not technologies or any(t in r["techs"] for t in technologies))
    ]
    if not filtered:
        filtered = deepcopy(_LINKEDIN_RECRUITERS)
    return {
        "recruiters": deepcopy(filtered),
        "totalFound": len(filtered),
        "count": len(filtered),
        "message": f"Found {len(filtered)} recruiters matching your criteria across {len(set(r['company'] for r in filtered))} companies.",
    }


def enrich_linkedin_profiles(urls: list, tech_context: str) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.enrich_linkedin_profiles(urls, tech_context)
    names = ["Sarah Johnson", "Tom Mitchell", "Priya Kapoor", "Alex Wong", "Maria Silva"]
    companies = ["TEKsystems", "Infosys", "Capgemini", "Wipro", "Accenture"]
    techs_list = [["Java", "Spring Boot"], ["Java", "AWS", "Docker"], ["Java", "Microservices"], ["Spring", "SQL"], ["Java", "DevOps"]]
    profiles = []
    for i, url in enumerate(urls[:5]):
        idx = i % len(names)
        name = names[idx]
        profiles.append({
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
        })
    return {
        "profiles": profiles,
        "enriched": len(profiles),
        "message": f"{len(profiles)} profiles enriched successfully via Apollo/Hunter.",
    }


def send_linkedin_outreach(recruiter_ids: list, subject: str, body: str, channel: str, schedule_at: Optional[str], user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.send_linkedin_outreach(recruiter_ids, subject, body, channel, schedule_at, user_external_id)
    names = [r["name"] for r in _LINKEDIN_RECRUITERS if r["id"] in recruiter_ids]
    if schedule_at:
        _LINKEDIN_SCHEDULED_OUTREACH.append(
            {
                "recruiterIds": list(recruiter_ids),
                "subject": subject,
                "body": body,
                "channel": channel,
                "scheduleAt": schedule_at,
                "status": "scheduled",
            }
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


def set_linkedin_recruiter_bookmark(recruiter_id: int, bookmarked: bool, user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.set_linkedin_recruiter_bookmark(recruiter_id, bookmarked, user_external_id)
    recruiter = next((row for row in _LINKEDIN_RECRUITERS if row["id"] == recruiter_id), None)
    if not recruiter:
        raise ValueError("Recruiter not found.")
    recruiter["bookmarked"] = bookmarked
    return {
        "success": True,
        "message": f"{recruiter['name']} {'saved to' if bookmarked else 'removed from'} your recruiter list.",
    }


def create_linkedin_message_template(name: str, body: str, user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.create_linkedin_message_template(name, body, user_external_id)
    normalized_name = name.strip()
    template = next(
        (row for row in _LINKEDIN_TEMPLATES if row["name"].casefold() == normalized_name.casefold()),
        None,
    )
    if template:
        template["body"] = body
    else:
        template = {"id": len(_LINKEDIN_TEMPLATES) + 1, "name": normalized_name, "body": body}
        _LINKEDIN_TEMPLATES.append(template)
    return deepcopy(template)


def generate_linkedin_message(prompt: str, message_type: str, tone: str, channel: str) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.generate_linkedin_message(prompt, message_type, tone, channel)
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
        "connect": "Hi {{recruiter_name}},\n\nI noticed your expertise in IT staffing at {{company}} and wanted to reach out. I have a Senior Java Developer with Spring Boot and AWS experience available immediately for C2C roles.\n\nWould love to connect!\n\n{{candidate_name}}",
        "inmail": "Hi {{recruiter_name}},\n\nHope this message finds you well! I am reaching out because I have a highly skilled Senior Java Developer currently available for C2C contract positions at {{company}}.\n\nKey highlights:\n• 8+ years Java, Spring Boot, Microservices\n• Cloud: AWS, Docker, Kubernetes\n• Location: {{location}} | Rate: $85-90/hr C2C\n• Availability: Immediate\n\nWould you be open to a quick conversation?\n\nBest,\n{{candidate_name}}",
        "cold_outreach": "Hi {{recruiter_name}},\n\nI hope this message finds you well. I'm reaching out because I have an excellent Senior Java Developer available for C2C contract roles.\n\nProfile Highlights:\n• 8+ years of Java development with Spring Boot, Microservices, and AWS expertise\n• Full-stack capabilities: Java backend, REST APIs, cloud architecture\n• Available immediately for long-term C2C engagements\n• Rate: $85-90/hr | {{location}}\n\nWould this be a fit for any current client needs?\n\nBest regards,\n{{candidate_name}}",
        "followup": "Hi {{recruiter_name}},\n\nJust following up on my earlier message. Our Java Developer remains available and is actively interviewing. Wanted to touch base before this window closes.\n\n{{candidate_name}}",
        "hotlist": "Hi {{recruiter_name}},\n\nI have a Senior Java Developer on our bench:\n• Skills: {{tech_stack}}\n• Experience: 8+ years\n• Location: {{location}}\n• Availability: Immediate | Rate: $85-90/hr C2C\n\nWould this profile be a fit for any open requirements?\n\n{{candidate_name}}",
        "thankyou": "Hi {{recruiter_name}},\n\nThank you so much for connecting! We appreciate your responsiveness and look forward to working together.\n\nPlease reach out anytime you have Java/{{tech_stack}} requirements.\n\nBest,\n{{candidate_name}}",
        "resume": "Hi {{recruiter_name}},\n\nAs discussed, please find attached the resume of our Senior Java Developer:\n• 8+ years Java, Spring Boot, Microservices\n• Cloud: AWS, Docker, Kubernetes\n• Available immediately · C2C · {{location}}\n\nLet me know if you need additional information.\n\nBest,\n{{candidate_name}}",
    }
    key = message_type if message_type in subjects else "cold_outreach"
    return {
        "subject": subjects[key],
        "message": bodies[key],
        "body": bodies[key],
        "messageType": key,
    }


def save_linkedin_settings(settings: dict, user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.save_linkedin_settings(settings, user_external_id)
    _LINKEDIN_SETTINGS.update(settings)
    return {"success": True, "message": "LinkedIn settings saved successfully."}


def save_linkedin_api_keys(keys: dict, user_external_id: str | None = None) -> dict:
    backend = _pg_backend()
    if backend:
        return backend.save_linkedin_api_keys(keys, user_external_id)
    connected = []
    status_map = {"apollo": "apollo", "hunter": "hunter", "rocketreach": "rocketreach", "lusha": "lusha"}
    for key, value in keys.items():
        if not value or not str(value).strip():
            continue
        connected.append(key)
        source_id = status_map.get(key)
        if source_id:
            for source in _LINKEDIN_API_SOURCES:
                if source.get("id") == source_id:
                    source["status"] = "connected"
    return {"success": True, "message": f"API keys saved for: {', '.join(connected) if connected else 'none'}."}


def get_endpoint_catalog() -> dict:
    backend = _pg_backend()
    if backend:
        return backend.get_endpoint_catalog()
    return {
        "items": [
            {
                "method": "GET",
                "path": "/health",
                "summary": "Service health with database status.",
                "requestExample": None,
                "responseExample": {
                    "status": "ok",
                    "database": {"status": "available", "message": "PostgreSQL connection succeeded."},
                    "modules": ["overview", "campaigns", "job-automation", "day-report", "submissions", "linkedin"],
                },
            },
            {
                "method": "POST",
                "path": "/api/auth/login",
                "summary": "Login and receive session token.",
                "requestExample": {"email": "admin@marketingmind.ai", "password": "Admin@123"},
                "responseExample": {"token": "uuid-token", "user": {"id": "u-admin-1", "name": "Admin User", "email": "admin@marketingmind.ai", "role": "admin"}},
            },
            {
                "method": "POST",
                "path": "/api/auth/register",
                "summary": "Register a new user.",
                "requestExample": {"name": "New User", "email": "new@example.com", "password": "Pass@123", "role": "user"},
                "responseExample": {"token": "uuid-token", "user": {"id": "u-xxx", "name": "New User", "email": "new@example.com", "role": "user"}},
            },
            {
                "method": "GET",
                "path": "/api/user/profile",
                "summary": "Get the authenticated user's profile.",
                "requestExample": None,
                "responseExample": {"user": {"id": "u-admin-1", "name": "Admin User", "email": "admin@marketingmind.ai", "role": "admin", "phone": "+1-555-0101", "company": "MarketingMind"}},
            },
            {
                "method": "PUT",
                "path": "/api/user/profile",
                "summary": "Update user profile fields.",
                "requestExample": {"name": "Admin User", "phone": "+1-555-0101", "company": "MarketingMind", "title": "Platform Administrator", "location": "San Francisco, CA"},
                "responseExample": {"success": True, "message": "Profile updated successfully."},
            },
            {
                "method": "GET",
                "path": "/api/overview",
                "summary": "Platform overview metrics and module list.",
                "requestExample": None,
                "responseExample": get_overview_payload(),
            },
            {
                "method": "GET",
                "path": "/api/campaigns/workspace",
                "summary": "Full campaign workspace with metrics, templates, and contacts.",
                "requestExample": None,
                "responseExample": {"metrics": {"emailsSent": 0, "openRate": 0, "replyRate": 0, "bounceRate": 2}},
            },
            {
                "method": "POST",
                "path": "/api/campaigns/preview",
                "summary": "Preview campaign subject/body before launch.",
                "requestExample": {
                    "subject": "Available consultants | {{candidate_name}}",
                    "body": "Hi {{company_name}},<br/>Sharing a strong profile.",
                    "recipients": ["buyer@example.com"],
                },
                "responseExample": preview_campaign(
                    "Available consultants | {{candidate_name}}",
                    "Hi {{company_name}},<br/>Sharing a strong profile.",
                    ["buyer@example.com"],
                ),
            },
            {
                "method": "POST",
                "path": "/api/campaigns/launch",
                "summary": "Launch or schedule a campaign.",
                "requestExample": {
                    "campaignName": "Data/AI Pulse",
                    "subject": "Senior Data Engineer available",
                    "body": "Profile summary",
                    "recipients": ["team@example.com"],
                    "scheduledFor": "2026-05-29 09:00",
                    "sendNow": False,
                },
                "responseExample": {"success": True, "message": "Campaign scheduled."},
            },
            {
                "method": "GET",
                "path": "/api/job-automation/workspace",
                "summary": "Full job automation workspace: profile, search, results, analysis.",
                "requestExample": None,
                "responseExample": {"stats": {"appliedToday": 6, "newMatches": 6, "interviews": 2, "avgMatchScore": 84}},
            },
            {
                "method": "PUT",
                "path": "/api/job-automation/profile",
                "summary": "Save candidate job profile.",
                "requestExample": deepcopy(_data()["job_profile"]),
                "responseExample": {"success": True, "message": "Job profile updated in test data."},
            },
            {
                "method": "POST",
                "path": "/api/job-automation/search/run",
                "summary": "Run portal search. postedWithin '1'=24h, '2'=48h.",
                "requestExample": {
                    "titles": ["Java Developer"],
                    "requiredSkills": ["Spring Boot"],
                    "optionalSkills": ["AWS"],
                    "location": "Texas",
                    "postedWithin": "2",
                },
                "responseExample": {"success": True, "message": "Search completed with 2 matching jobs.", "results": _data()["job_results"][:2]},
            },
            {
                "method": "POST",
                "path": "/api/job-automation/apply",
                "summary": "Apply to selected jobs (eligible if posted within 48h). supervised background apply; no UI browser open.",
                "requestExample": {"jobIds": [1, 2], "supervised": True},
                "responseExample": {
                    "success": True,
                    "message": "Started supervised apply for 2 job(s). Background portal apply has started.",
                    "applied": 2,
                    "applications": [],
                    "openUrls": [],
                    "supervised": True,
                },
            },
            {
                "method": "POST",
                "path": "/api/job-automation/auto-apply",
                "summary": "Scrape 24h+48h portals and route ≥65% apply / 40–64% tailor / <40% reject.",
                "requestExample": {"matchThreshold": 65},
                "responseExample": {
                    "success": True,
                    "message": "Scraped portals for 1d + 2d. Routed apply/tailor/reject.",
                    "applied": 2,
                    "tailored": 1,
                    "rejected": 1,
                    "jobIds": [1, 2],
                    "postedWindows": ["1", "2"],
                    "matchPolicy": {"applyMin": 65, "tailorMin": 40, "rejectBelow": 40},
                    "results": [],
                },
            },
            {
                "method": "POST",
                "path": "/api/job-automation/analyze",
                "summary": "Run CV match analysis against a job.",
                "requestExample": {"jobId": 1},
                "responseExample": {"selectedJobId": 1, "score": 89, "summary": "Strong fit.", "hits": ["Java", "Spring Boot"], "misses": ["Kubernetes"]},
            },
            {
                "method": "POST",
                "path": "/api/job-automation/resume/tailor",
                "summary": "Tailor CV to a job description (used for 40–64% match band).",
                "requestExample": {"jobId": 1},
                "responseExample": {"success": True, "jobId": 1, "tailoredScore": 78, "content": "...", "message": "Resume tailored."},
            },
            {
                "method": "GET",
                "path": "/api/job-automation/resumes",
                "summary": "List multi-resume CV library with isolated profileSnapshot metadata.",
                "requestExample": None,
                "responseExample": {"resumes": [{"id": 1, "fileName": "cv.pdf", "isActive": True}]},
            },
            {
                "method": "POST",
                "path": "/api/job-automation/resumes/{resume_id}/activate",
                "summary": "Activate a CV and restore its isolated profileSnapshot.",
                "requestExample": None,
                "responseExample": {"success": True, "message": "Active CV switched.", "resumes": []},
            },
            {
                "method": "POST",
                "path": "/api/job-automation/save",
                "summary": "Toggle save/bookmark a job (requires auth).",
                "requestExample": {"jobId": 1},
                "responseExample": {"success": True, "message": "Job saved to favorites.", "saved": True},
            },
            {
                "method": "POST",
                "path": "/api/job-automation/portals",
                "summary": "Add a job portal to the automation queue.",
                "requestExample": {"name": "Dice", "url": "https://www.dice.com"},
                "responseExample": {"name": "Dice", "url": "https://www.dice.com", "status": "Active"},
            },
            {
                "method": "POST",
                "path": "/api/job-automation/carriers",
                "summary": "Add a company career page to monitor.",
                "requestExample": {"name": "TCS Careers", "url": "https://www.tcs.com/careers"},
                "responseExample": {"name": "TCS Careers", "url": "https://www.tcs.com/careers"},
            },
            {
                "method": "GET",
                "path": "/api/day-report/dashboard",
                "summary": "Day-to-day recruiter performance dashboard.",
                "requestExample": None,
                "responseExample": {"range": {"start": "2026-05-12", "end": "2026-05-21"}, "recruiters": ["Komal", "Sam"], "totals": {"linkedin": 100, "calls": 80}},
            },
            {
                "method": "POST",
                "path": "/api/day-report/filter",
                "summary": "Filter recruiter dashboard rows.",
                "requestExample": {"start": "2026-05-13", "end": "2026-05-15", "recruiter": "Komal"},
                "responseExample": filter_day_report("2026-05-13", "2026-05-15", "Komal"),
            },
            {
                "method": "GET",
                "path": "/api/submissions/dashboard",
                "summary": "Submission progress with MoM and YoY comparisons.",
                "requestExample": None,
                "responseExample": {"range": {"start": "2025-11", "end": "2026-05"}, "months": []},
            },
            {
                "method": "POST",
                "path": "/api/submissions/filter",
                "summary": "Filter submission progress by month range.",
                "requestExample": {"startMonth": "2026-01", "endMonth": "2026-05"},
                "responseExample": filter_submissions("2026-01", "2026-05"),
            },
            {
                "method": "GET",
                "path": "/api/linkedin/workspace",
                "summary": "LinkedIn recruiter discovery workspace.",
                "requestExample": None,
                "responseExample": {"stats": {}, "recruiters": []},
            },
            {
                "method": "POST",
                "path": "/api/linkedin/discover",
                "summary": "Discover LinkedIn recruiters by company/technology.",
                "requestExample": {"companies": ["TCS", "Infosys"], "technologies": ["Java"], "seniority": "Senior", "location": "Dallas, TX", "connections": "2nd", "resultsPerCompany": 5},
                "responseExample": {"recruiters": [], "totalFound": 0, "message": "Discovery completed."},
            },
            {
                "method": "GET",
                "path": "/api/meta/test-data",
                "summary": "Export full backend test dataset JSON.",
                "requestExample": None,
                "responseExample": {"counts": {"campaign_contacts": 6, "job_results": 6}},
            },
            {
                "method": "POST",
                "path": "/api/meta/test-data/append",
                "summary": "Append records to an appendable dataset.",
                "requestExample": {"dataset": "campaign_contacts", "entries": [{"name": "Priya N", "email": "priya@example.com", "company": "Acme", "status": "Queued", "list": "Priority Accounts"}]},
                "responseExample": {"success": True, "message": "Appended 1 record(s) to campaign_contacts.", "dataset": "campaign_contacts", "totalRecords": 7},
            },
            {
                "method": "POST",
                "path": "/api/meta/test-data/reset",
                "summary": "Reset runtime test data back to baseline JSON.",
                "requestExample": None,
                "responseExample": {"success": True, "message": "Test data reset to baseline JSON."},
            },
        ]
    }


# ── User Profile Management ────────────────────────────────────────────


_USER_PROFILES: Dict[str, Dict[str, Any]] = {
    "u-admin-1": {
        "id": "u-admin-1",
        "name": "Admin User",
        "email": "admin@marketingmind.ai",
        "role": "admin",
        "phone": "+1-555-0101",
        "company": "MarketingMind",
        "title": "Platform Administrator",
        "department": "Operations",
        "location": "San Francisco, CA",
        "timezone": "America/Los_Angeles",
        "bio": "Platform admin managing campaign operations and recruiter dashboards.",
        "createdAt": "2025-01-01T00:00:00Z",
        "lastLogin": "2026-06-13T18:30:00Z",
    },
    "u-super-1": {
        "id": "u-super-1",
        "name": "Super Admin",
        "email": "superadmin@marketingmind.ai",
        "role": "super_admin",
        "phone": "+1-555-0102",
        "company": "MarketingMind",
        "title": "Chief Operations Officer",
        "department": "Executive",
        "location": "New York, NY",
        "timezone": "America/New_York",
        "bio": "Leading the MarketingMind platform and overseeing all operations.",
        "createdAt": "2024-12-01T00:00:00Z",
        "lastLogin": "2026-06-13T22:15:00Z",
    },
    "u-user-1": {
        "id": "u-user-1",
        "name": "Read Only User",
        "email": "user@marketingmind.ai",
        "role": "user",
        "phone": "+1-555-0103",
        "company": "MarketingMind",
        "title": "Campaign Analyst",
        "department": "Marketing",
        "location": "Austin, TX",
        "timezone": "America/Chicago",
        "bio": "Analyzing campaign performance and reporting insights.",
        "createdAt": "2026-02-15T00:00:00Z",
        "lastLogin": "2026-06-13T16:45:00Z",
    },
}

_USER_SETTINGS: Dict[str, Dict[str, Any]] = {
    "u-admin-1": {
        "notifications": {
            "emailNotifications": True,
            "campaignAlerts": True,
            "jobAlerts": True,
            "dailyReport": False,
            "weeklyDigest": True,
            "smsNotifications": False,
            "smsPhone": "",
        },
        "language": "en",
        "dateFormat": "MM/DD/YYYY",
        "theme": "light",
    },
    "u-super-1": {
        "notifications": {
            "emailNotifications": True,
            "campaignAlerts": True,
            "jobAlerts": True,
            "dailyReport": True,
            "weeklyDigest": True,
            "smsNotifications": False,
            "smsPhone": "",
        },
        "language": "en",
        "dateFormat": "MM/DD/YYYY",
        "theme": "light",
    },
    "u-user-1": {
        "notifications": {
            "emailNotifications": True,
            "campaignAlerts": False,
            "jobAlerts": True,
            "dailyReport": False,
            "weeklyDigest": False,
            "smsNotifications": False,
            "smsPhone": "",
        },
        "language": "en",
        "dateFormat": "MM/DD/YYYY",
        "theme": "light",
    },
}


def get_user_profile(user_id: str) -> dict:
    backend = _pg_backend()
    if backend:
        from app.services import pg_auth

        return pg_auth.get_user_profile(user_id)
    if user_id not in _USER_PROFILES:
        now_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        _USER_PROFILES[user_id] = {
            "id": user_id,
            "name": "User",
            "email": "",
            "role": "user",
            "phone": "",
            "company": "MarketingMind",
            "title": "",
            "department": "",
            "location": "",
            "timezone": "UTC",
            "bio": "",
            "createdAt": now_iso,
            "lastLogin": now_iso,
        }
    return deepcopy(_USER_PROFILES[user_id])


def update_user_profile(user_id: str, updates: dict) -> None:
    backend = _pg_backend()
    if backend:
        from app.services import pg_auth

        pg_auth.update_user_profile(user_id, updates)
        return
    if user_id not in _USER_PROFILES:
        # Auto-initialize profile before updating
        get_user_profile(user_id)

    allowed_fields = {"name", "phone", "company", "title", "department", "location", "timezone", "bio"}
    for key in updates:
        if key not in allowed_fields:
            continue
        _USER_PROFILES[user_id][key] = updates[key]


def change_user_password(user_id: str, current_password: str, new_password: str, confirm_password: str) -> None:
    backend = _pg_backend()
    if backend:
        from app.services import pg_auth

        pg_auth.change_user_password(user_id, current_password, new_password, confirm_password)
        return
    if new_password != confirm_password:
        raise ValueError("New passwords do not match.")

    if len(new_password) < 6:
        raise ValueError("Password must be at least 6 characters.")

    # In production, verify current_password against hashed value in database
    # For demo, we just accept any current password
    return


def get_user_settings(user_id: str) -> dict:
    backend = _pg_backend()
    if backend:
        from app.services import pg_auth

        return pg_auth.get_user_settings(user_id)
    if user_id not in _USER_SETTINGS:
        _USER_SETTINGS[user_id] = {
            "notifications": {
                "emailNotifications": True,
                "campaignAlerts": True,
                "jobAlerts": True,
                "dailyReport": False,
                "weeklyDigest": True,
                "smsNotifications": False,
                "smsPhone": "",
            },
            "language": "en",
            "dateFormat": "MM/DD/YYYY",
            "theme": "light",
        }
    return deepcopy(_USER_SETTINGS[user_id])


def update_user_settings(user_id: str, settings: dict) -> None:
    backend = _pg_backend()
    if backend:
        from app.services import pg_auth

        pg_auth.update_user_settings(user_id, settings)
        return
    if user_id not in _USER_SETTINGS:
        _USER_SETTINGS[user_id] = settings
    else:
        _USER_SETTINGS[user_id].update(settings)
