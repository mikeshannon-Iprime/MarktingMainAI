"""Apify LinkedIn job scraping — https://apify.com/api/job-scraping-api"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.config import get_settings
from app.services.portal_scraper import existing_job_keys

_SKILL_PATTERN = re.compile(
    r"\b(java|python|javascript|typescript|react|angular|vue|node\.?js|spring|aws|azure|"
    r"docker|kubernetes|sql|postgresql|mongodb|fastapi|django|\.net|c#|golang|go|scala|"
    r"kafka|redis|graphql|microservices|devops|terraform|spark|hadoop|machine learning|"
    r"data engineer|full stack|backend|frontend)\b",
    re.IGNORECASE,
)


def apify_configured() -> bool:
    settings = get_settings()
    token = settings.apify_api_token or ""
    return bool(token.strip()) and settings.use_apify_scraper


def _api_token() -> str:
    settings = get_settings()
    token = (settings.apify_api_token or "").strip()
    if not token:
        raise RuntimeError("APIFY_API_TOKEN is not configured.")
    return token


def _api_request(method: str, path: str, payload: Optional[dict] = None, timeout: int = 60) -> dict:
    token = _api_token()
    separator = "&" if "?" in path else "?"
    url = f"https://api.apify.com/v2{path}{separator}token={urllib.parse.quote(token)}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _actor_path(actor_id: str) -> str:
    return f"/acts/{actor_id.replace('/', '~')}/runs"


def build_linkedin_search_url(
    title: str,
    location: str = "",
    posted_within: str | int = "3",
) -> str:
    params = {"keywords": title.strip(), "position": "1", "pageNum": "0"}
    if location.strip():
        params["location"] = location.strip()
    try:
        posted_days = max(1, min(30, int(posted_within)))
    except (TypeError, ValueError):
        posted_days = 3
    params["f_TPR"] = f"r{posted_days * 86400}"
    return "https://www.linkedin.com/jobs/search/?" + urllib.parse.urlencode(params)


def _extract_skills(*texts: str) -> List[str]:
    found: List[str] = []
    for text in texts:
        if not text:
            continue
        for match in _SKILL_PATTERN.findall(text):
            normalized = match.lower().replace("node.js", "node")
            if normalized not in found:
                found.append(normalized.title() if normalized.islower() else match)
    return found[:8]


def _posted_days_ago(posted_at: Optional[str]) -> str:
    if not posted_at:
        return "3"
    try:
        if "T" in posted_at:
            posted_date = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
        else:
            posted_date = datetime.strptime(posted_at[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - posted_date
        return str(max(1, min(30, delta.days or 1)))
    except Exception:
        return "3"


def _format_rate(salary_info: Any) -> str:
    if isinstance(salary_info, list) and salary_info:
        return " – ".join(str(item) for item in salary_info[:2])
    if isinstance(salary_info, str) and salary_info.strip():
        return salary_info.strip()
    return ""


def _map_apify_item(item: dict, *, job_id: int, portal: Dict[str, str]) -> Dict[str, Any]:
    title = (item.get("title") or item.get("jobTitle") or "Open Role").strip()
    company = (item.get("companyName") or item.get("company") or "Unknown Company").strip()
    location = (item.get("location") or "Remote").strip()
    description = (
        item.get("descriptionText")
        or item.get("description")
        or item.get("descriptionHtml")
        or ""
    )
    if description and "<" in description:
        from app.services.job_detail_fetcher import html_to_text

        description = html_to_text(description)
    skills = _extract_skills(title, description, item.get("jobFunction") or "")
    employment = (item.get("employmentType") or "Contract").strip()
    link = item.get("link") or item.get("applyUrl") or portal.get("url", "")
    quality = "full" if len(description.strip()) >= 180 else ("summary" if description.strip() else "placeholder")
    return {
        "id": job_id,
        "role": title,
        "company": company,
        "location": location,
        "type": employment,
        "posted": _posted_days_ago(item.get("postedAt")),
        "rate": _format_rate(item.get("salaryInfo")),
        "match": 0,
        "hot": False,
        "skills": skills,
        "portalName": portal.get("name") or "LinkedIn (Apify)",
        "portalUrl": portal.get("url") or "https://www.linkedin.com/jobs/",
        "sourceUrl": link,
        "description": description[:16000] if description else f"{title} at {company}.",
        "descriptionQuality": quality if description else "placeholder",
        "scrapeSource": "apify",
        "externalId": str(item.get("id") or ""),
    }


def _wait_for_run(run_id: str, max_wait_seconds: int) -> dict:
    deadline = time.time() + max_wait_seconds
    while time.time() < deadline:
        payload = _api_request("GET", f"/actor-runs/{run_id}", timeout=30)
        data = payload.get("data") or {}
        status = (data.get("status") or "").upper()
        if status in {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}:
            return data
        time.sleep(3)
    raise TimeoutError(f"Apify actor run {run_id} did not finish within {max_wait_seconds}s.")


def _fetch_dataset_items(dataset_id: str) -> List[dict]:
    token = _api_token()
    url = (
        f"https://api.apify.com/v2/datasets/{dataset_id}/items"
        f"?token={urllib.parse.quote(token)}&format=json&clean=true"
    )
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=120) as response:
        items = json.loads(response.read().decode("utf-8"))
    return items if isinstance(items, list) else []


def scrape_linkedin_jobs_apify(
    portal: Dict[str, str],
    *,
    titles: List[str],
    location: str,
    existing_jobs: List[Dict[str, Any]],
    next_job_id: int,
    posted_within: str | int = "3",
    count: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """Scrape LinkedIn jobs via Apify actor (curious_coder/linkedin-jobs-scraper)."""
    settings = get_settings()
    if not apify_configured():
        return [], next_job_id

    target_titles = [title.strip() for title in titles if title and title.strip()]
    if not target_titles:
        target_titles = ["Software Engineer"]

    urls = [
        build_linkedin_search_url(title, location, posted_within)
        for title in target_titles[:3]
    ]
    run_input = {
        "urls": urls,
        "count": count or settings.apify_jobs_per_search,
        "scrapeCompany": False,
    }

    try:
        started = _api_request(
            "POST",
            _actor_path(settings.apify_actor_id),
            payload=run_input,
            timeout=60,
        )
        run_data = started.get("data") or {}
        run_id = run_data.get("id")
        dataset_id = run_data.get("defaultDatasetId")
        if not run_id:
            raise RuntimeError("Apify did not return a run id.")

        finished = _wait_for_run(run_id, settings.apify_max_wait_seconds)
        if (finished.get("status") or "").upper() != "SUCCEEDED":
            raise RuntimeError(f"Apify run failed with status {finished.get('status')}.")

        dataset_id = dataset_id or (finished.get("defaultDatasetId"))
        if not dataset_id:
            raise RuntimeError("Apify run succeeded but no dataset id was returned.")

        items = _fetch_dataset_items(dataset_id)
    except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Apify LinkedIn scrape failed: {exc}") from exc

    seen = existing_job_keys(existing_jobs)
    scraped: List[Dict[str, Any]] = []
    job_id = next_job_id

    for item in items:
        if not isinstance(item, dict):
            continue
        mapped = _map_apify_item(item, job_id=job_id, portal=portal)
        key = (
            mapped["role"].strip().lower(),
            mapped["company"].strip().lower(),
            mapped["portalName"].strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        scraped.append(mapped)
        job_id += 1

    return scraped, job_id


def is_linkedin_portal(portal: Dict[str, str]) -> bool:
    blob = f"{portal.get('name', '')} {portal.get('url', '')}".lower()
    return "linkedin" in blob
