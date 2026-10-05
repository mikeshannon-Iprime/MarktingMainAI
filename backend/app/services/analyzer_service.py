"""Production Analyzer helpers: match scoring, surgical resume tailor, reviewable autofill."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.services.job_match_ai import (
    _embedding_job_score,
    _heuristic_job_score,
    profile_to_cv_text,
)
from app.services.resume_ai import _ml_skill_assessment

SKILL_CATALOG = [
    "Java",
    "Python",
    "Spring Boot",
    "AWS",
    "Kubernetes",
    "React",
    "TypeScript",
    "SQL",
    "Docker",
    "Kafka",
    "GraphQL",
    "Microservices",
    "Azure",
    "GCP",
    "Node.js",
    "CI/CD",
    "Terraform",
    "REST APIs",
    "Agile",
    "Maven",
    "Git",
]

# Fields that must stay human-reviewable before portal submit.
SENSITIVE_AUTOFILL_KEYS = frozenset(
    {
        "visa",
        "workAuthorization",
        "authorization",
        "ssn",
        "socialSecurity",
        "salary",
        "rate",
        "desiredSalary",
        "citizenship",
        "disability",
        "veteran",
        "gender",
        "race",
        "ethnicity",
    }
)

PLATFORM_HINTS = (
    ("linkedin", "LinkedIn"),
    ("indeed", "Indeed"),
    ("dice", "Dice"),
    ("monster", "Monster"),
    ("careerbuilder", "CareerBuilder"),
    ("ziprecruiter", "ZipRecruiter"),
)

ADJUSTMENTS_MARKER = "=== ROLE-ALIGNED ADJUSTMENTS"
JD_POINTERS_MARKER = "=== JD-ALIGNED EXPERIENCE POINTERS"
BASE_RESUME_MARKER = "=== BASE RESUME (preserved)"


def detect_platform(job: Optional[Dict[str, Any]] = None, text: str = "") -> str:
    blob = " ".join(
        [
            str((job or {}).get("portalName") or ""),
            str((job or {}).get("sourceUrl") or ""),
            str((job or {}).get("portalUrl") or ""),
            text or "",
        ]
    ).lower()
    for needle, label in PLATFORM_HINTS:
        if needle in blob:
            return label
    if job and job.get("portalName"):
        return str(job["portalName"])
    return "Job board"


def find_skills_in_text(text: str, extra: Optional[List[str]] = None) -> List[str]:
    catalog = list(dict.fromkeys([*(extra or []), *SKILL_CATALOG]))
    lowered = (text or "").lower()
    found: List[str] = []
    for skill in catalog:
        if skill.lower() in lowered:
            found.append(skill)
    return found


def _unique(items: List[str]) -> List[str]:
    return list(dict.fromkeys([str(item).strip() for item in items if str(item).strip()]))


def build_match_analysis(
    *,
    profile: Dict[str, Any],
    selected_job: Optional[Dict[str, Any]],
    job_description: str,
    job_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Score CV vs JD with embeddings when available; always return keyword hits/misses."""
    description = (job_description or "").strip()
    if not description and selected_job:
        description = (
            selected_job.get("description")
            or (
                f"{selected_job.get('role')} at {selected_job.get('company')} in {selected_job.get('location')}. "
                f"Required skills: {', '.join(selected_job.get('skills') or [])}. "
                f"Employment type: {selected_job.get('type') or 'Contract'}."
            )
        )
    if not description:
        description = "General software engineering role requiring cloud and API experience."

    cv_skills = _unique(
        list(profile.get("resumeSkills") or [])
        or [
            "Java",
            "Spring Boot",
            "Python",
            "React",
            "AWS",
            "Docker",
            "Maven",
            "Git",
            "Agile",
            "REST APIs",
            "TypeScript",
        ]
    )
    job_skills = _unique(list((selected_job or {}).get("skills") or []))
    jd_skills = find_skills_in_text(description, extra=cv_skills + job_skills)
    required = _unique(job_skills + jd_skills)

    desc_lower = description.lower()
    hits = [skill for skill in required if skill.lower() in desc_lower and any(skill.lower() == cv.lower() for cv in cv_skills)]
    # Also count CV skills explicitly mentioned in the JD.
    for skill in cv_skills:
        if skill.lower() in desc_lower and skill not in hits:
            hits.append(skill)
    hits = _unique(hits)

    titles = profile.get("jobTitles") if isinstance(profile.get("jobTitles"), list) else []
    target_role = (
        (selected_job or {}).get("role")
        or (titles[0] if titles else None)
        or "Software Engineer"
    )
    assessment = _ml_skill_assessment(
        f"{profile_to_cv_text(profile)}\n{description}",
        target_role,
        required or jd_skills,
    )
    assessment_hits = _unique(list(assessment.get("matchedSkills") or []))
    assessment_misses = _unique(list(assessment.get("missingSkills") or []))
    hits = _unique(hits + assessment_hits)

    misses = [skill for skill in required if skill not in hits]
    misses = _unique(misses + assessment_misses + [s for s in jd_skills if s not in hits])[:10]

    job_payload = dict(selected_job or {})
    job_payload["description"] = description
    job_payload.setdefault("role", "target role")
    job_payload.setdefault("skills", required)

    score: int
    insight: str
    match_source: str
    if selected_job or description:
        score, insight, match_source = _embedding_job_score(profile, job_payload)
        if match_source == "ml":
            heuristic_score, heuristic_insight = _heuristic_job_score(
                profile,
                job_payload,
                required,
                job_payload.get("role") or "",
            )
            score = max(score, heuristic_score)
            insight = f"{insight} {heuristic_insight}".strip()
            match_source = "heuristic+ml"
    else:
        score, insight = 72, "Baseline score without a job description."
        match_source = "baseline"

    # Blend keyword coverage so missing-keyword UI stays meaningful.
    if required:
        coverage = round((len(hits) / max(len(required), 1)) * 100)
        score = max(40, min(98, round((score * 0.7) + (coverage * 0.3))))
    else:
        score = max(40, min(98, score))

    skill_gaps = misses[:6]
    recommendations = [
        f"Add a concise bullet that demonstrates '{miss}' with a measurable outcome."
        for miss in skill_gaps[:4]
    ]
    if not recommendations:
        recommendations = [
            "Re-order recent experience so the most role-aligned project appears first.",
            "Add one quantified outcome (latency, revenue, adoption) to your top bullet.",
        ]
    recommendations.append(
        "Keep your employment history intact — only emphasize overlapping skills for this posting."
    )

    role_label = (selected_job or {}).get("role") or "target role"
    company_label = (selected_job or {}).get("company") or "the employer"
    platform = detect_platform(selected_job, description)

    return {
        "selectedJobId": (selected_job or {}).get("id") if selected_job else job_id,
        "score": int(score),
        "summary": (
            f"{platform} analysis for {role_label} at {company_label}: "
            f"{score}% match. {insight}"
        ),
        "hits": hits if hits else required[:3],
        "misses": misses if misses else ["Leadership metrics", "Portfolio link"],
        "suggestions": recommendations,
        "skillGaps": skill_gaps,
        "recommendations": recommendations,
        "experienceMatch": (
            f"Your listed experience ({profile.get('experience') or 'see CV'}) "
            f"can be framed against {role_label} without rewriting tenure dates."
        ),
        "titleMatch": f"'{role_label}' aligns with your profile titles/skills for this posting.",
        "jobDescription": description,
        "tailoredScore": None,
        "matchSource": match_source,
        "platform": platform,
        "sourceUrl": (selected_job or {}).get("sourceUrl") or (selected_job or {}).get("portalUrl"),
        "missingKeywords": misses if misses else ["Leadership metrics", "Portfolio link"],
    }


def _extract_base_resume_body(content: str) -> str:
    text = (content or "").strip()
    if not text:
        return ""
    if ADJUSTMENTS_MARKER in text:
        text = text.split(ADJUSTMENTS_MARKER, 1)[0].strip()
    if BASE_RESUME_MARKER in text:
        text = text.split(BASE_RESUME_MARKER, 1)[-1].strip()
    return text


def build_base_resume_text(
    *,
    profile: Dict[str, Any],
    active_resume: Optional[Dict[str, Any]] = None,
    existing_tailored: str = "",
) -> str:
    """Prefer an existing tailored/base body so we never invent a full rewrite."""
    preserved = _extract_base_resume_body(existing_tailored)
    if len(preserved) >= 40:
        return preserved

    summary = (
        (active_resume or {}).get("summary")
        or profile.get("resumeSummary")
        or profile.get("summary")
        or ""
    )
    skills = _unique(
        list((active_resume or {}).get("skills") or [])
        or list(profile.get("resumeSkills") or [])
    )
    lines = [
        profile.get("name") or "Candidate",
        " | ".join(
            part
            for part in [
                profile.get("email") or "",
                profile.get("phone") or "",
                profile.get("location") or "",
            ]
            if part
        ),
    ]
    if profile.get("linkedin"):
        lines.append(str(profile["linkedin"]))
    lines.extend(["", "PROFESSIONAL SUMMARY", summary.strip() or "Experienced professional seeking the next role-aligned engagement."])
    if skills:
        lines.extend(["", "KEY SKILLS", ", ".join(skills)])
    if profile.get("experience"):
        lines.extend(["", "EXPERIENCE", str(profile["experience"])])
    return "\n".join(lines).strip()


def extract_jd_requirements(job_description: str, *, limit: int = 8) -> List[str]:
    """Pull concrete requirement / responsibility phrases from a full JD."""
    text = (job_description or "").strip()
    if not text:
        return []

    requirements: List[str] = []
    section = re.search(
        r"(?is)(?:responsibilities|requirements|qualifications|what you(?:'|’)ll do|"
        r"must[- ]have|required skills|key responsibilities)\s*[:\-]?\s*(.+?)(?:\n\s*\n|"
        r"benefits|about (?:us|the company)|nice to have|preferred|$)",
        text,
    )
    blob = section.group(1) if section else text
    for raw in re.split(r"[\n•●▪◦\-\u2022]+", blob):
        line = re.sub(r"\s+", " ", raw).strip(" .;:")
        if not (28 <= len(line) <= 180):
            continue
        lowered = line.lower()
        if lowered.startswith(("http", "www.", "email", "phone")):
            continue
        if any(token in lowered for token in ("equal opportunity", "click here", "apply now")):
            continue
        requirements.append(line)
        if len(requirements) >= limit:
            break
    return _unique(requirements)


def craft_jd_pointer(requirement: str, *, cv_skills: List[str], hits: List[str]) -> Optional[str]:
    """Turn a JD requirement into a resume-style bullet grounded in known CV skills."""
    req = re.sub(r"\s+", " ", (requirement or "").strip(" .;:"))
    if not req:
        return None
    overlap = [
        skill
        for skill in _unique([*(hits or []), *(cv_skills or [])])
        if skill.lower() in req.lower()
    ]
    focus = ", ".join(overlap[:3]) if overlap else "related delivery work already on your CV"
    cleaned = re.sub(r"(?i)^(responsible for|you will|the ideal candidate will)\s+", "", req)
    cleaned = cleaned[0].upper() + cleaned[1:] if cleaned else req
    if overlap:
        return f"{cleaned} — emphasize existing {focus} experience already reflected in your resume."
    return (
        f"{cleaned} — add only if you already performed comparable work; "
        "do not invent new employers or dates."
    )


def build_surgical_tailor(
    *,
    profile: Dict[str, Any],
    selected_job: Dict[str, Any],
    analysis: Dict[str, Any],
    active_resume: Optional[Dict[str, Any]] = None,
    existing_tailored: str = "",
) -> Dict[str, Any]:
    """Suggest role-aligned adjustments and JD-derived bullets without rewriting employment history."""
    base = build_base_resume_text(
        profile=profile,
        active_resume=active_resume,
        existing_tailored=existing_tailored,
    )
    role = selected_job.get("role") or "target role"
    company = selected_job.get("company") or "target company"
    jd_text = analysis.get("jobDescription") or selected_job.get("description") or ""
    hits = list(analysis.get("hits") or [])[:6]
    misses = list(analysis.get("misses") or analysis.get("missingKeywords") or [])[:5]
    cv_skills = list(profile.get("resumeSkills") or [])

    jd_requirements = extract_jd_requirements(jd_text, limit=8)
    jd_pointers: List[str] = []
    for requirement in jd_requirements[:6]:
        pointer = craft_jd_pointer(requirement, cv_skills=cv_skills, hits=hits)
        if pointer:
            jd_pointers.append(pointer)

    adjustments: List[str] = []
    if hits:
        adjustments.append(
            f"Lead with overlapping strengths already on your CV: {', '.join(hits)}."
        )
    for miss in misses[:3]:
        adjustments.append(
            f"If you have genuine exposure to '{miss}', add one short bullet under your most recent role — "
            "do not invent experience."
        )
    if jd_pointers:
        adjustments.append(
            f"Incorporate the {len(jd_pointers)} JD-aligned experience pointer(s) below into the most relevant recent role."
        )
    adjustments.append(
        f"Tune the opening summary sentence toward {role} at {company}; keep dates and employers unchanged."
    )
    adjustments.append(
        "Do not rebuild your career narrative — only reorder emphasis and keyword coverage for this posting."
    )

    sections = [
        f"{BASE_RESUME_MARKER}\n{base}",
        f"{ADJUSTMENTS_MARKER} (for {role} @ {company}) ===\n"
        + "\n".join(f"- {item}" for item in adjustments),
    ]
    if jd_pointers:
        sections.append(
            f"{JD_POINTERS_MARKER} (from job description) ===\n"
            + "\n".join(f"• {item}" for item in jd_pointers)
        )
    content = "\n\n".join(sections) + "\n"
    boosted = min(
        98,
        int(analysis.get("score") or 0) + 4 + min(len(hits), 4) + min(len(jd_pointers), 3),
    )
    return {
        "content": content,
        "adjustments": adjustments,
        "jdPointers": jd_pointers,
        "tailoredScore": boosted,
        "basePreserved": True,
    }


def apply_adjustment_to_content(content: str, suggestion: str) -> str:
    """Append a single accepted suggestion under the adjustments block."""
    suggestion = (suggestion or "").strip()
    if not suggestion:
        return content or ""
    body = (content or "").rstrip()
    bullet = f"- {suggestion}"
    if bullet in body or suggestion in body:
        return body + ("\n" if not body.endswith("\n") else "")
    if ADJUSTMENTS_MARKER in body:
        return body + "\n" + bullet + "\n"
    return (
        f"{body}\n\n{ADJUSTMENTS_MARKER} ===\n{bullet}\n"
        if body
        else f"{ADJUSTMENTS_MARKER} ===\n{bullet}\n"
    )


def build_autofill_preview(
    *,
    profile: Dict[str, Any],
    selected_job: Optional[Dict[str, Any]] = None,
    approved_keys: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Map repeated application fields; mark sensitive / work-auth for review."""
    approved = {str(key) for key in (approved_keys or [])}
    job = selected_job or {}

    titles = profile.get("jobTitles") if isinstance(profile.get("jobTitles"), list) else []
    target_title = (titles[0] if titles else None) or job.get("role") or ""

    field_defs: List[Tuple[str, str, str, bool]] = [
        ("fullName", "Full name", str(profile.get("name") or ""), False),
        ("email", "Email", str(profile.get("email") or ""), False),
        ("phone", "Phone", str(profile.get("phone") or ""), False),
        ("location", "Location / city", str(profile.get("location") or ""), False),
        ("linkedin", "LinkedIn URL", str(profile.get("linkedin") or ""), False),
        ("experience", "Years of experience", str(profile.get("experience") or ""), False),
        ("employmentType", "Employment type", str(profile.get("employmentType") or job.get("type") or ""), False),
        ("workMode", "Work mode", str(profile.get("workMode") or ""), False),
        ("jobTitle", "Target title", str(target_title), False),
        ("skills", "Skills summary", ", ".join(profile.get("resumeSkills") or [])[:240], False),
        ("rate", "Desired rate / salary", str(profile.get("rate") or ""), True),
        ("visa", "Work authorization / visa", str(profile.get("visa") or ""), True),
    ]

    fields: List[Dict[str, Any]] = []
    auto_fill_count = 0
    review_count = 0
    for key, label, value, force_sensitive in field_defs:
        sensitive = force_sensitive or key in SENSITIVE_AUTOFILL_KEYS
        value = (value or "").strip()
        if not value:
            continue
        approved_flag = (not sensitive) or (key in approved)
        status = "approved" if approved_flag else "needs_review"
        if status == "approved":
            auto_fill_count += 1
        else:
            review_count += 1
        fields.append(
            {
                "key": key,
                "label": label,
                "value": value,
                "sensitive": sensitive,
                "requiresReview": sensitive,
                "status": status,
                "approved": approved_flag,
            }
        )

    platform = detect_platform(job)
    return {
        "success": True,
        "jobId": job.get("id"),
        "platform": platform,
        "role": job.get("role"),
        "company": job.get("company"),
        "fields": fields,
        "autoFillCount": auto_fill_count,
        "reviewCount": review_count,
        "message": (
            f"Prepared {len(fields)} application fields for {platform}. "
            f"{review_count} sensitive answer(s) held for review."
            if fields
            else "No profile fields available to autofill yet."
        ),
    }
