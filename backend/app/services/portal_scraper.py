"""Portal scraping and resilient fallback generation for job automation."""

from __future__ import annotations

import html
import json
import logging
import random
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Set, Tuple
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import get_settings

logger = logging.getLogger(__name__)

COMPANY_PREFIXES = [
    "Northwind",
    "Atlas",
    "Signal",
    "Lattice",
    "Summit",
    "Vertex",
    "Pinnacle",
    "Harbor",
    "Cobalt",
    "Meridian",
]
COMPANY_SUFFIXES = ["Systems", "Digital", "Labs", "Solutions", "Technologies", "Corp", "Group"]
EMPLOYMENT_TYPES = ["C2C", "W2", "C2H", "Full Time"]
LOCATIONS = ["Dallas, TX", "Austin, TX", "Remote", "Chicago, IL", "Houston, TX", "New York, NY"]
DICE_POSTED_DATE_FILTERS = {
    "1": "ONE",
    "2": "THREE",  # Dice has no 48h bucket; THREE is the closest public filter
    "3": "THREE",
    "7": "SEVEN",
}
DICE_NEXT_PAYLOAD_PATTERN = re.compile(
    r'self\.__next_f\.push\(\[1,("(?:\\.|[^"\\])*")\]\)'
)


def _compute_match(title: str, skills: List[str], required_skills: List[str]) -> int:
    if not required_skills:
        return random.randint(72, 94)
    title_blob = title.lower()
    hits = 0
    for skill in required_skills:
        normalized = skill.lower().strip()
        if not normalized:
            continue
        if normalized in title_blob:
            hits += 1
            continue
        if any(normalized in candidate.lower() for candidate in skills):
            hits += 1
    base = 62 + hits * 9
    return min(98, base + random.randint(0, 5))


def _clean_search_title(title: str) -> str:
    """Normalize a job title so it works as a portal search query."""
    cleaned = " ".join((title or "").split())
    # Keep only the leading segment of pipe-delimited headlines
    # (e.g. "Solutions Architect | AI, Cloud, Data" -> "Solutions Architect").
    if "|" in cleaned:
        cleaned = cleaned.split("|", 1)[0]
    cleaned = cleaned.strip(" .,;:-")
    if len(cleaned) > 80:
        cleaned = cleaned[:80].rsplit(" ", 1)[0].strip(" .,;:-")
    return cleaned or "Software Engineer"


def _clean_search_location(location: str) -> str:
    """Return a plausible location, falling back when the field holds junk data."""
    cleaned = " ".join((location or "").split()).strip(" .,;:-")
    looks_invalid = (
        not cleaned
        or len(cleaned) > 40
        or "|" in cleaned
        or "http" in cleaned.lower()
    )
    return "United States" if looks_invalid else cleaned


def _posted_days(posted_within: str | int) -> int:
    try:
        return max(1, min(30, int(posted_within)))
    except (TypeError, ValueError):
        return 3


def build_portal_search_url(
    portal: Dict[str, str],
    title: str,
    location: str,
    *,
    posted_within: str | int = "3",
    keyword: str | None = None,
) -> str:
    """Build a working public search URL for common job portals."""
    portal_name = (portal.get("name") or "").strip().lower()
    base_url = (portal.get("url") or "").rstrip("/")
    clean_title = _clean_search_title(keyword or title)
    clean_location = _clean_search_location(location)
    posted_days = _posted_days(posted_within)

    if "dice" in portal_name or "dice.com" in base_url.lower():
        posted_filter = DICE_POSTED_DATE_FILTERS.get(str(posted_within), "THREE")
        query = urlencode(
            [
                ("filters.postedDate", posted_filter),
                ("countryCode", "US"),
                ("location", clean_location),
                ("q", clean_title),
            ]
        )
        return f"https://www.dice.com/jobs?{query}"
    if "monster" in portal_name or "monster.com" in base_url.lower():
        # Monster currently exposes no stable public date URL parameter. The
        # backend applies posted_within after scraping/fallback generation.
        query = urlencode([("q", clean_title), ("where", clean_location), ("page", "1")])
        return f"https://www.monster.com/jobs/search?{query}"
    if "careerbuilder" in portal_name or "careerbuilder.com" in base_url.lower():
        query = urlencode(
            [("keywords", clean_title), ("location", clean_location), ("posted", posted_days)]
        )
        return f"https://www.careerbuilder.com/jobs?{query}"
    if "linkedin" in portal_name or "linkedin.com" in base_url.lower():
        query = urlencode(
            [
                ("keywords", clean_title),
                ("location", clean_location),
                ("f_TPR", f"r{posted_days * 86400}"),
            ]
        )
        return f"https://www.linkedin.com/jobs/search/?{query}"
    if "indeed" in portal_name or "indeed.com" in base_url.lower():
        query = urlencode([("q", clean_title), ("l", clean_location), ("fromage", posted_days)])
        return f"https://www.indeed.com/jobs?{query}"
    if "ziprecruiter" in portal_name or "ziprecruiter.com" in base_url.lower():
        zip_days = next((day for day in (1, 5, 10, 30) if posted_days <= day), 30)
        query = urlencode(
            [("search", clean_title), ("location", clean_location), ("days", zip_days)]
        )
        return f"https://www.ziprecruiter.com/jobs-search?{query}"

    if not base_url:
        return ""
    separator = "&" if "?" in base_url else "?"
    generic_query = urlencode(
        [
            ("q", clean_title),
            ("location", clean_location),
            ("postedWithin", posted_days),
            ("countryCode", "US"),
        ]
    )
    return f"{base_url}{separator}{generic_query}"


def is_dice_portal(portal: Dict[str, str]) -> bool:
    portal_name = (portal.get("name") or "").lower()
    portal_url = (portal.get("url") or "").lower()
    return "dice" in portal_name or "dice.com" in portal_url


def _extract_dice_jobs(page_html: str) -> List[Dict[str, Any]]:
    """Extract Dice's server-rendered job list from Next.js flight payloads."""
    for match in DICE_NEXT_PAYLOAD_PATTERN.finditer(html.unescape(page_html)):
        try:
            payload = json.loads(match.group(1))
        except (TypeError, json.JSONDecodeError):
            continue
        marker = '"jobList":{"data":'
        marker_index = payload.find(marker)
        if marker_index < 0:
            continue
        raw_jobs = payload[marker_index + len(marker):]
        try:
            jobs, _ = json.JSONDecoder().raw_decode(raw_jobs)
        except json.JSONDecodeError:
            continue
        if isinstance(jobs, list):
            return [job for job in jobs if isinstance(job, dict)]
    return []


def _posted_age_days(posted_date: str | None) -> int:
    if not posted_date:
        return 0
    try:
        posted = datetime.fromisoformat(posted_date.replace("Z", "+00:00"))
        return max(0, (datetime.now(timezone.utc) - posted).days)
    except (TypeError, ValueError):
        return 0


def scrape_dice_jobs(
    portal: Dict[str, str],
    *,
    titles: List[str],
    skills: List[str],
    required_skills: List[str],
    location: str,
    posted_within: str | int,
    existing_jobs: List[Dict[str, Any]],
    next_job_id: int,
    max_results: int = 10,
    timeout_seconds: int = 15,
) -> tuple[List[Dict[str, Any]], int]:
    """Fetch and map live Dice jobs; callers retain fallback behavior on failure."""
    query_term = next(
        (value.strip() for value in required_skills + skills + titles if value and value.strip()),
        "Software Engineer",
    )
    search_url = build_portal_search_url(
        portal,
        titles[0] if titles else query_term,
        location,
        posted_within=posted_within,
        keyword=query_term,
    )
    request = Request(
        search_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - fixed HTTPS URL
        page = response.read().decode("utf-8", errors="replace")

    raw_jobs = _extract_dice_jobs(page)
    seen = existing_job_keys(existing_jobs)
    scraped: List[Dict[str, Any]] = []
    job_id = next_job_id

    for item in raw_jobs:
        role = str(item.get("title") or "").strip()
        company = str(item.get("companyName") or "").strip()
        detail_url = str(item.get("detailsPageUrl") or "").strip()
        if not role or not company or not detail_url.startswith("https://www.dice.com/job-detail/"):
            continue
        key = (role.lower(), company.lower(), "dice")
        if key in seen:
            continue

        job_location = item.get("jobLocation") if isinstance(item.get("jobLocation"), dict) else {}
        display_location = (
            str(job_location.get("displayName") or "").strip()
            or ("Remote" if item.get("isRemote") else _clean_search_location(location))
        )
        summary = str(item.get("summary") or "").strip()
        employment_type = str(item.get("employmentType") or "Full Time").strip()
        role_skills = list(dict.fromkeys((required_skills or [])[:3] + (skills or [])[:3]))[:6]
        match_score = _compute_match(role, role_skills, required_skills)
        posted_days = _posted_age_days(item.get("postedDate"))

        scraped.append(
            {
                "id": job_id,
                "role": role,
                "company": company,
                "location": display_location,
                "type": employment_type,
                "posted": str(posted_days),
                "rate": str(item.get("salary") or "").replace("$$", "$"),
                "match": match_score,
                "hot": match_score >= 90,
                "skills": role_skills,
                "portalName": portal.get("name") or "Dice",
                "portalUrl": portal.get("url") or "https://www.dice.com",
                "sourceUrl": detail_url,
                "description": summary or f"{role} at {company}. Live job from Dice.",
                "descriptionQuality": "summary" if summary else "placeholder",
                "scrapeSource": "dice_live",
                "easyApply": bool(item.get("easyApply")),
            }
        )
        seen.add(key)
        job_id += 1
        if len(scraped) >= max_results:
            break

    if scraped:
        try:
            from app.services.job_detail_fetcher import enrich_jobs_with_detail_descriptions

            settings = get_settings()
            enrich_jobs_with_detail_descriptions(
                scraped,
                max_fetch=min(len(scraped), max(4, settings.dice_jobs_per_search)),
                timeout_seconds=min(12, timeout_seconds or settings.dice_scrape_timeout_seconds),
            )
        except Exception as exc:
            logger.warning("Dice detail JD enrich failed: %s", exc)

    return scraped, job_id


def build_scraped_job(
    *,
    job_id: int,
    portal: Dict[str, str],
    title: str,
    skills: List[str],
    location: str,
    required_skills: List[str],
    posted_within: str | int,
    offset: int,
) -> Dict[str, Any]:
    company = f"{COMPANY_PREFIXES[offset % len(COMPANY_PREFIXES)]} {COMPANY_SUFFIXES[offset % len(COMPANY_SUFFIXES)]}"
    posted = str(random.randint(1, 7))
    role_skills = list(dict.fromkeys((skills or [])[:4] + (required_skills or [])[:3]))[:6]
    if not role_skills:
        role_skills = ["Java", "Spring Boot", "AWS"]
    match_score = _compute_match(title, role_skills, required_skills)
    return {
        "id": job_id,
        "role": title,
        "company": company,
        "location": location or LOCATIONS[offset % len(LOCATIONS)],
        "type": EMPLOYMENT_TYPES[offset % len(EMPLOYMENT_TYPES)],
        "posted": posted,
        "rate": f"${70 + offset * 3}–{88 + offset * 3}/hr",
        "match": match_score,
        "hot": match_score >= 90,
        "skills": role_skills,
        "portalName": portal["name"],
        "portalUrl": portal["url"],
        "sourceUrl": build_portal_search_url(
            portal,
            title,
            location,
            posted_within=posted_within,
            keyword=(required_skills or skills or [title])[0],
        ),
        "description": (
            f"{title} at {company} in {location or 'Remote'}. "
            f"Scraped from {portal['name']}. Skills: {', '.join(role_skills)}."
        ),
        "descriptionQuality": "placeholder",
        "scrapeSource": "synthetic",
    }


def existing_job_keys(jobs: List[Dict[str, Any]]) -> Set[Tuple[str, str, str]]:
    keys: Set[Tuple[str, str, str]] = set()
    for job in jobs:
        keys.add(
            (
                (job.get("role") or "").strip().lower(),
                (job.get("company") or "").strip().lower(),
                (job.get("portalName") or job.get("portal_name") or "").strip().lower(),
            )
        )
    return keys


def scrape_portal_jobs(
    portals: List[Dict[str, str]],
    *,
    titles: List[str],
    skills: List[str],
    required_skills: List[str],
    location: str,
    existing_jobs: List[Dict[str, Any]],
    next_job_id: int,
    posted_within: str | int = "3",
    max_per_portal: int = 3,
) -> tuple[List[Dict[str, Any]], int]:
    """Return newly scraped jobs and the next available job id."""
    if not portals:
        return [], next_job_id

    active_portals = [portal for portal in portals if (portal.get("status") or "Active") == "Active"]
    if not active_portals:
        active_portals = portals

    target_titles = [title.strip() for title in titles if title and title.strip()]
    if not target_titles:
        target_titles = ["Software Engineer", "Java Developer"]

    seen = existing_job_keys(existing_jobs)
    scraped: List[Dict[str, Any]] = []
    job_id = next_job_id
    offset = 0

    for portal in active_portals:
        portal_titles = target_titles[:max_per_portal]
        for title in portal_titles:
            candidate = build_scraped_job(
                job_id=job_id,
                portal=portal,
                title=title,
                skills=skills,
                location=location,
                required_skills=required_skills,
                posted_within=posted_within,
                offset=offset,
            )
            offset += 1
            key = (
                candidate["role"].strip().lower(),
                candidate["company"].strip().lower(),
                candidate["portalName"].strip().lower(),
            )
            if key in seen:
                continue
            seen.add(key)
            scraped.append(candidate)
            job_id += 1

    return scraped, job_id


def scrape_all_portal_jobs(
    portals: List[Dict[str, str]],
    *,
    titles: List[str],
    skills: List[str],
    required_skills: List[str],
    location: str,
    existing_jobs: List[Dict[str, Any]],
    next_job_id: int,
    posted_within: str | int = "3",
    max_per_portal: int = 3,
) -> tuple[List[Dict[str, Any]], int]:
    """Scrape all portals — Apify for LinkedIn when configured, simulated fallback otherwise."""
    if not portals:
        return [], next_job_id

    active_portals = [portal for portal in portals if (portal.get("status") or "Active") == "Active"]
    if not active_portals:
        active_portals = portals

    scraped: List[Dict[str, Any]] = []
    job_id = next_job_id
    working_existing = list(existing_jobs)

    try:
        from app.services.apify_scraper import (
            apify_configured,
            is_linkedin_portal,
            scrape_linkedin_jobs_apify,
        )
    except ImportError:
        apify_configured = lambda: False  # type: ignore[assignment]
        is_linkedin_portal = lambda _portal: False  # type: ignore[assignment]
        scrape_linkedin_jobs_apify = None  # type: ignore[assignment]

    apify_used = False
    settings = get_settings()
    for portal in active_portals:
        portal_batch: List[Dict[str, Any]] = []
        if settings.dice_live_scraping_enabled and is_dice_portal(portal):
            try:
                portal_batch, job_id = scrape_dice_jobs(
                    portal,
                    titles=titles,
                    skills=skills,
                    required_skills=required_skills,
                    location=location,
                    posted_within=posted_within,
                    existing_jobs=working_existing,
                    next_job_id=job_id,
                    max_results=settings.dice_jobs_per_search,
                    timeout_seconds=settings.dice_scrape_timeout_seconds,
                )
            except Exception as exc:
                logger.warning("Live Dice scrape failed; using fallback jobs: %s", exc)
        elif apify_configured() and is_linkedin_portal(portal) and scrape_linkedin_jobs_apify:
            try:
                portal_batch, job_id = scrape_linkedin_jobs_apify(
                    portal,
                    titles=titles,
                    location=location,
                    existing_jobs=working_existing,
                    next_job_id=job_id,
                    posted_within=posted_within,
                )
                apify_used = True
            except Exception as exc:
                logger.warning("Apify scrape failed for %s: %s", portal.get("name"), exc)
        if not portal_batch:
            portal_batch, job_id = scrape_portal_jobs(
                [portal],
                titles=titles,
                skills=skills,
                required_skills=required_skills,
                location=location,
                posted_within=posted_within,
                existing_jobs=working_existing,
                next_job_id=job_id,
                max_per_portal=max_per_portal,
            )
        scraped.extend(portal_batch)
        working_existing.extend(portal_batch)

    if apify_used:
        for job in scraped:
            job.setdefault("scrapeSource", "apify")

    try:
        from app.services.job_detail_fetcher import enrich_jobs_with_detail_descriptions

        enrich_jobs_with_detail_descriptions(
            [job for job in scraped if job.get("scrapeSource") != "synthetic"],
            max_fetch=12,
            timeout_seconds=12,
        )
    except Exception as exc:
        logger.warning("Portal detail JD enrich failed: %s", exc)

    return scraped, job_id
