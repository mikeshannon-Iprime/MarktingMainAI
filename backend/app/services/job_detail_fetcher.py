"""Fetch exact job title + description from portal/vendor detail pages."""

from __future__ import annotations

import html
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)

MAX_DESCRIPTION_CHARS = 16000
MIN_FULL_DESCRIPTION_CHARS = 180
MIN_USABLE_DESCRIPTION_CHARS = 80

PLACEHOLDER_MARKERS = (
    "live job from dice",
    "scraped from",
    "general software engineering role",
)

TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_STYLE_RE = re.compile(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>")
WHITESPACE_RE = re.compile(r"[ \t\f\v]+")
NEWLINE_RE = re.compile(r"\n{3,}")
NEXT_DATA_RE = re.compile(
    r'<script[^>]+id="__NEXT_DATA__"[^>]*>(?P<body>.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
JSON_LD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(?P<body>.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
META_DESC_RE = re.compile(
    r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]+content=["\'](?P<body>[^"\']+)["\']',
    re.IGNORECASE,
)
TITLE_TAG_RE = re.compile(r"(?is)<title[^>]*>(?P<body>.*?)</title>")
DICE_DETAIL_RE = re.compile(
    r"https?://(?:www\.)?dice\.com/job-detail/[a-zA-Z0-9\-]+",
    re.IGNORECASE,
)
DICE_DETAIL_REL_RE = re.compile(r"/job-detail/[a-zA-Z0-9\-]+", re.IGNORECASE)
INDEED_VIEW_RE = re.compile(
    r"https?://(?:www\.)?indeed\.com/viewjob\?[^\s\"'<>]+",
    re.IGNORECASE,
)
LINKEDIN_VIEW_RE = re.compile(
    r"https?://(?:www\.)?linkedin\.com/jobs/view/\d+",
    re.IGNORECASE,
)
MONSTER_JOB_RE = re.compile(
    r"https?://(?:www\.)?monster\.com/job-openings/[^\s\"'<>]+",
    re.IGNORECASE,
)


def html_to_text(raw_html: str) -> str:
    cleaned = SCRIPT_STYLE_RE.sub(" ", raw_html or "")
    cleaned = TAG_RE.sub(" ", cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = WHITESPACE_RE.sub(" ", cleaned)
    cleaned = NEWLINE_RE.sub("\n\n", cleaned.replace("\r", "\n"))
    return cleaned.strip()


def is_placeholder_description(description: str, *, role: str = "", company: str = "") -> bool:
    text = (description or "").strip()
    if not text:
        return True
    lowered = text.lower()
    if any(marker in lowered for marker in PLACEHOLDER_MARKERS):
        return True
    if role and company and text.lower() == f"{role.lower()} at {company.lower()}.":
        return True
    if len(text) < MIN_FULL_DESCRIPTION_CHARS and "responsibilit" not in lowered and "requirement" not in lowered:
        return True
    return False


def is_search_listing_url(url: str) -> bool:
    lowered = (url or "").lower()
    if not lowered.startswith(("http://", "https://")):
        return False
    if "/job-detail/" in lowered or "/jobs/view/" in lowered or "/viewjob" in lowered:
        return False
    return any(
        token in lowered
        for token in (
            "/jobs/search",
            "/job-search",
            "/jobs-search",
            "/jobs?",
            "q=",
            "keyword=",
            "keywords=",
            "search=",
        )
    )


def _clip_description(text: str) -> str:
    value = (text or "").strip()
    if len(value) <= MAX_DESCRIPTION_CHARS:
        return value
    return value[:MAX_DESCRIPTION_CHARS].rsplit(" ", 1)[0].strip()


def _walk_json(node: Any, found: Dict[str, str]) -> None:
    if isinstance(node, dict):
        keys = {str(k).lower(): k for k in node.keys()}
        for title_key in ("title", "jobtitle", "job_title", "name"):
            if title_key in keys and not found.get("title"):
                value = node.get(keys[title_key])
                if isinstance(value, str) and 3 <= len(value.strip()) <= 200:
                    found["title"] = value.strip()
        for desc_key in (
            "description",
            "descriptiontext",
            "description_text",
            "jobdescription",
            "job_description",
            "jobdescriptionhtml",
            "textdescription",
            "summary",
            "details",
            "abouttherole",
            "about_the_role",
        ):
            if desc_key in keys:
                value = node.get(keys[desc_key])
                if isinstance(value, str) and len(value.strip()) >= MIN_USABLE_DESCRIPTION_CHARS:
                    text = html_to_text(value) if "<" in value else value.strip()
                    # Prefer longer / richer descriptions.
                    if len(text) > len(found.get("description") or ""):
                        found["description"] = text
        for value in node.values():
            _walk_json(value, found)
    elif isinstance(node, list):
        for item in node:
            _walk_json(item, found)


def _extract_from_json_blobs(page: str) -> Dict[str, str]:
    found: Dict[str, str] = {}
    next_match = NEXT_DATA_RE.search(page or "")
    if next_match:
        try:
            payload = json.loads(next_match.group("body"))
            _walk_json(payload, found)
        except json.JSONDecodeError:
            pass

    # Dice / Next.js flight payloads often embed escaped JSON without __NEXT_DATA__.
    for match in re.finditer(r'self\.__next_f\.push\(\[1,("(?:\\.|[^"\\])*")\]\)', page or ""):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, str):
            continue
        # Prefer explicit job description fragments.
        for marker in ('"description":"', '"jobDescription":"', '"descriptionText":"'):
            idx = payload.find(marker)
            if idx < 0:
                continue
            try:
                value, _ = json.JSONDecoder().raw_decode(payload[idx + len(marker) - 1 :])
            except json.JSONDecodeError:
                continue
            if isinstance(value, str) and len(value.strip()) >= MIN_USABLE_DESCRIPTION_CHARS:
                text = html_to_text(value) if "<" in value else value.strip()
                if len(text) > len(found.get("description") or ""):
                    found["description"] = text
        title_idx = payload.find('"title":"')
        if title_idx >= 0 and not found.get("title"):
            try:
                title, _ = json.JSONDecoder().raw_decode(payload[title_idx + len('"title":') :])
                if isinstance(title, str) and 3 <= len(title.strip()) <= 200:
                    found["title"] = title.strip()
            except json.JSONDecodeError:
                pass

    for match in JSON_LD_RE.finditer(page or ""):
        try:
            payload = json.loads(match.group("body"))
        except json.JSONDecodeError:
            continue
        nodes = payload if isinstance(payload, list) else [payload]
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_type = str(node.get("@type") or "").lower()
            if "jobposting" in node_type or not found.get("description"):
                title = node.get("title") or node.get("name")
                description = node.get("description")
                if isinstance(title, str) and title.strip():
                    found.setdefault("title", title.strip())
                if isinstance(description, str) and description.strip():
                    text = html_to_text(description)
                    if len(text) > len(found.get("description") or ""):
                        found["description"] = text
    return found


def _extract_generic_html(page: str) -> Dict[str, str]:
    found: Dict[str, str] = {}
    title_match = TITLE_TAG_RE.search(page or "")
    if title_match:
        title = html_to_text(title_match.group("body"))
        title = re.sub(r"\s*[\|\-–].*$", "", title).strip()
        if title:
            found["title"] = title

    section_patterns = [
        r'(?is)<(?:div|section|article)[^>]*(?:id|class)=["\'][^"\']*(?:job[-_ ]?description|jobDescription|description__text|job-details|jobDescriptionText)[^"\']*["\'][^>]*>(?P<body>.*?)</(?:div|section|article)>',
        r'(?is)<(?:div|section)[^>]*data-testid=["\'](?:jobDescription|job-description|description|jobDescriptionText)["\'][^>]*>(?P<body>.*?)</(?:div|section)>',
        r'(?is)<(?:div|section)[^>]*(?:itemprop)=["\']description["\'][^>]*>(?P<body>.*?)</(?:div|section)>',
    ]
    for pattern in section_patterns:
        match = re.search(pattern, page or "")
        if match:
            text = html_to_text(match.group("body"))
            if len(text) >= MIN_USABLE_DESCRIPTION_CHARS:
                found["description"] = text
                break

    if not found.get("description"):
        meta = META_DESC_RE.search(page or "")
        if meta:
            found["description"] = html.unescape(meta.group("body")).strip()
    return found


def fetch_url_html(url: str, *, timeout_seconds: int = 18) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
        },
        method="GET",
    )
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - caller supplies job URLs
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def _normalize_detail_candidates(page: str, base_url: str) -> List[str]:
    urls: List[str] = []
    urls.extend(DICE_DETAIL_RE.findall(page or ""))
    for rel in DICE_DETAIL_REL_RE.findall(page or ""):
        urls.append(f"https://www.dice.com{rel}")
    urls.extend(INDEED_VIEW_RE.findall(page or ""))
    urls.extend(LINKEDIN_VIEW_RE.findall(page or ""))
    urls.extend(MONSTER_JOB_RE.findall(page or ""))

    # Absolute-ize relative links for common boards.
    host = urlparse(base_url).netloc.lower()
    for rel in re.findall(r'href=["\']([^"\']+)["\']', page or "", flags=re.IGNORECASE):
        if rel.startswith("/job-detail/"):
            urls.append(f"https://www.dice.com{rel}")
        elif "indeed.com" in host and "/viewjob" in rel:
            urls.append(rel if rel.startswith("http") else f"https://www.indeed.com{rel}")
        elif "linkedin.com" in host and "/jobs/view/" in rel:
            urls.append(rel if rel.startswith("http") else f"https://www.linkedin.com{rel}")

    cleaned: List[str] = []
    seen = set()
    for url in urls:
        value = html.unescape(url).split("#")[0].strip()
        if not value or value in seen:
            continue
        seen.add(value)
        cleaned.append(value)
    return cleaned


def _score_candidate(url: str, role: str, company: str, page: str) -> int:
    score = 0
    role_l = (role or "").lower().strip()
    company_l = (company or "").lower().strip()
    # Look at a local window around the URL occurrence for title/company hints.
    idx = (page or "").lower().find(url.lower().replace("https://www.dice.com", ""))
    if idx < 0:
        idx = (page or "").lower().find(url.lower())
    window = (page or "")[max(0, idx - 400) : idx + 400].lower() if idx >= 0 else (page or "").lower()
    if role_l:
        tokens = [tok for tok in re.split(r"\W+", role_l) if len(tok) >= 3][:4]
        score += sum(3 for tok in tokens if tok in window)
    if company_l and company_l.split(",")[0].strip() in window:
        score += 5
    if "/job-detail/" in url or "/jobs/view/" in url or "/viewjob" in url:
        score += 2
    return score


def resolve_detail_url_from_search(
    search_url: str,
    *,
    role: str = "",
    company: str = "",
    timeout_seconds: int = 18,
) -> Tuple[str, str]:
    """Return (detail_url, search_html) for the best matching posting on a search page."""
    page = fetch_url_html(search_url, timeout_seconds=timeout_seconds)
    candidates = _normalize_detail_candidates(page, search_url)
    if not candidates:
        return "", page
    ranked = sorted(
        candidates,
        key=lambda url: _score_candidate(url, role, company, page),
        reverse=True,
    )
    return ranked[0], page


def fetch_job_detail(
    url: str,
    *,
    timeout_seconds: int = 18,
    role: str = "",
    company: str = "",
) -> Dict[str, str]:
    """Return {title, description, descriptionQuality, sourceUrl, resolvedUrl}."""
    result = {
        "title": "",
        "description": "",
        "descriptionQuality": "missing",
        "sourceUrl": url,
        "resolvedUrl": "",
        "message": "",
    }
    if not url or not str(url).startswith(("http://", "https://")):
        result["message"] = "No portal URL available."
        return result

    target_url = url
    try:
        if is_search_listing_url(url):
            detail_url, _ = resolve_detail_url_from_search(
                url,
                role=role,
                company=company,
                timeout_seconds=timeout_seconds,
            )
            if not detail_url:
                result["message"] = (
                    "This result points to a search page, not a single posting, "
                    "and no job-detail link could be resolved."
                )
                return result
            target_url = detail_url
            result["resolvedUrl"] = detail_url

        page = fetch_url_html(target_url, timeout_seconds=timeout_seconds)
    except Exception as exc:
        logger.warning("Job detail fetch failed for %s: %s", target_url, exc)
        result["message"] = f"Portal page request failed: {exc}"
        return result

    extracted = _extract_from_json_blobs(page)
    if not extracted.get("description") or len(extracted.get("description") or "") < MIN_FULL_DESCRIPTION_CHARS:
        generic = _extract_generic_html(page)
        if len(generic.get("description") or "") > len(extracted.get("description") or ""):
            extracted["description"] = generic["description"]
        if generic.get("title") and not extracted.get("title"):
            extracted["title"] = generic["title"]

    title = (extracted.get("title") or "").strip()
    description = _clip_description(extracted.get("description") or "")
    result["title"] = title
    result["description"] = description
    result["sourceUrl"] = target_url
    if description and not is_placeholder_description(description, role=title or role, company=company):
        result["descriptionQuality"] = "full"
        result["message"] = "Fetched full job description from the portal posting."
    elif description:
        result["descriptionQuality"] = "summary"
        result["message"] = "Fetched a partial job description from the portal posting."
    else:
        result["message"] = "Portal page loaded but no job description block was found."
    return result


def enrich_jobs_with_detail_descriptions(
    jobs: List[Dict[str, Any]],
    *,
    max_fetch: int = 8,
    timeout_seconds: int = 15,
) -> List[Dict[str, Any]]:
    """Mutate jobs in place: pull exact JD/title from detail pages when needed."""
    fetched = 0
    for job in jobs:
        source_url = str(job.get("sourceUrl") or "").strip()
        current = str(job.get("description") or "")
        role = str(job.get("role") or "")
        company = str(job.get("company") or "")
        needs_detail = is_placeholder_description(current, role=role, company=company)
        if not needs_detail:
            job.setdefault(
                "descriptionQuality",
                "full" if len(current) >= MIN_FULL_DESCRIPTION_CHARS else "summary",
            )
            continue
        if fetched >= max_fetch or not source_url.startswith("http"):
            job.setdefault("descriptionQuality", "placeholder" if needs_detail else "summary")
            continue
        detail = fetch_job_detail(
            source_url,
            timeout_seconds=timeout_seconds,
            role=role,
            company=company,
        )
        fetched += 1
        if detail.get("description") and not is_placeholder_description(
            detail["description"],
            role=detail.get("title") or role,
            company=company,
        ):
            job["description"] = detail["description"]
            job["descriptionQuality"] = detail.get("descriptionQuality") or "full"
            if detail.get("resolvedUrl"):
                job["sourceUrl"] = detail["resolvedUrl"]
            elif detail.get("sourceUrl") and not is_search_listing_url(detail["sourceUrl"]):
                job["sourceUrl"] = detail["sourceUrl"]
            if detail.get("title") and (
                not role
                or role.lower() in {"untitled role", "open role"}
                or len(detail["title"]) >= 3
            ):
                if len(detail["title"]) >= len(role) * 0.6:
                    job["role"] = detail["title"]
            job["scrapeSource"] = job.get("scrapeSource") or "detail_page"
        else:
            job.setdefault("descriptionQuality", "placeholder" if needs_detail else "summary")
    return jobs
