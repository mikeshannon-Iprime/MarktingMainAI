"""CV ↔ job description matching for Sales Automation / job-board workflows."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from app.services.embedding_service import (
    embedding_model_name,
    embedding_similarity_percent,
    embeddings_available,
    get_embedding_status,
)
from app.services.llm_client import invoke_llm, llm_available
from app.services.resume_ai import _ml_skill_assessment, _safe_parse_json

MatchPipeline = Dict[str, Any]


def profile_to_cv_text(profile: Dict[str, Any]) -> str:
    parts: List[str] = []
    if profile.get("name"):
        parts.append(f"Name: {profile['name']}")
    if profile.get("resumeSummary"):
        parts.append(profile["resumeSummary"])
    if profile.get("jobTitles"):
        parts.append("Target titles: " + ", ".join(profile["jobTitles"]))
    if profile.get("resumeSkills"):
        parts.append("Skills: " + ", ".join(profile["resumeSkills"]))
    if profile.get("experience"):
        parts.append(f"Experience: {profile['experience']}")
    if profile.get("location"):
        parts.append(f"Location: {profile['location']}")
    return "\n".join(parts).strip()


def job_to_description(job: Dict[str, Any]) -> str:
    skills = ", ".join(job.get("skills") or [])
    description = job.get("description") or ""
    return (
        f"Role: {job.get('role', '')}\n"
        f"Company: {job.get('company', '')}\n"
        f"Location: {job.get('location', '')}\n"
        f"Type: {job.get('type', '')}\n"
        f"Skills: {skills}\n"
        f"Description: {description}"
    ).strip()


def _heuristic_job_score(
    profile: Dict[str, Any],
    job: Dict[str, Any],
    required_skills: List[str],
    target_role: str,
) -> Tuple[int, str]:
    cv_text = profile_to_cv_text(profile)
    job_text = job_to_description(job)
    assessment = _ml_skill_assessment(
        f"{cv_text}\n{job_text}",
        target_role or job.get("role", "Software Engineer"),
        required_skills,
    )
    portal_score = int(job.get("match") or 0)
    heuristic = int(assessment.get("matchScore") or 0)
    if portal_score:
        blended = round((heuristic * 0.65) + (portal_score * 0.35))
    else:
        blended = heuristic
    insight = (
        f"Matched {len(assessment.get('matchedSkills') or [])} required skill(s); "
        f"portal score {portal_score}%." if portal_score else
        f"Matched {len(assessment.get('matchedSkills') or [])} required skill(s)."
    )
    return max(0, min(100, blended)), insight


def _embedding_job_score(
    profile: Dict[str, Any],
    job: Dict[str, Any],
) -> Tuple[int, str, str]:
    cv_text = profile_to_cv_text(profile)
    job_text = job_to_description(job)
    portal_score = int(job.get("match") or 0)

    if embeddings_available():
        embed_score = embedding_similarity_percent(cv_text, job_text)
        if portal_score:
            blended = round((embed_score * 0.8) + (portal_score * 0.2))
            insight = (
                f"Embedding similarity {embed_score}% ({embedding_model_name().split('/')[-1]}); "
                f"blended with portal score {portal_score}%."
            )
        else:
            blended = embed_score
            insight = f"Embedding similarity {embed_score}% ({embedding_model_name().split('/')[-1]})."
        return max(0, min(100, blended)), insight, "embeddings"

    blended, insight = _heuristic_job_score(profile, job, [], job.get("role", ""))
    return blended, f"{insight} (embedding model unavailable; TF-IDF fallback.)", "ml"


def _llm_explain_jobs(
    profile: Dict[str, Any],
    jobs: List[Dict[str, Any]],
    target_role: str,
) -> Tuple[Dict[int, Dict[str, Any]], Dict[str, Any]]:
    if not jobs:
        return {}, {"provider": "none", "status": "skipped"}

    cv_text = profile_to_cv_text(profile)[:8000]
    job_blocks = []
    for job in jobs[:15]:
        job_blocks.append(
            f"ID {job['id']}: {job.get('role', '')} @ {job.get('company', '')}\n"
            f"{job_to_description(job)[:1200]}"
        )

    system_prompt = (
        "You are a staffing automation reasoning layer. "
        "Do NOT replace embedding scores — only explain fit. "
        "Return ONLY valid JSON array: "
        '[{"jobId": number, "roleClassification": "string", '
        '"rankingExplanation": "short reason", "skillGaps": ["gap1"]}]. '
        "Focus on skill extraction alignment, role classification, ranking explanation, and gap analysis."
    )
    user_prompt = (
        f"Target role: {target_role}\n\n"
        f"Candidate CV:\n{cv_text}\n\n"
        f"Top ranked jobs (embedding similarity already computed):\n"
        f"{'---'.join(job_blocks)}\n"
    )

    raw_content, meta = invoke_llm(
        system_prompt,
        user_prompt,
        timeout_seconds=30,
        skip_if_unavailable=True,
    )
    if meta.get("status") != "ok" or not raw_content:
        return {"__meta__": meta}, meta

    parsed = _safe_parse_json(raw_content)
    if isinstance(parsed, list):
        rows = parsed
    elif isinstance(parsed, dict) and isinstance(parsed.get("results"), list):
        rows = parsed["results"]
    else:
        rows = _extract_explanation_array(raw_content)

    explained: Dict[int, Dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        job_id = row.get("jobId") or row.get("id")
        if job_id is None:
            continue
        gaps = row.get("skillGaps") or row.get("gaps") or []
        if not isinstance(gaps, list):
            gaps = [str(gaps)]
        explained[int(job_id)] = {
            "roleClassification": str(row.get("roleClassification") or row.get("role") or ""),
            "rankingExplanation": str(
                row.get("rankingExplanation")
                or row.get("rationale")
                or row.get("explanation")
                or "LLM fit explanation."
            ),
            "skillGaps": [str(g) for g in gaps if g],
        }
    return explained, meta


def _extract_explanation_array(raw_content: str) -> List[Dict[str, Any]]:
    match = re.search(r"\[[\s\S]*\]", raw_content)
    if not match:
        return []
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def _format_llm_insight(base_insight: str, llm_row: Dict[str, Any]) -> str:
    parts = [base_insight]
    role = llm_row.get("roleClassification")
    if role:
        parts.append(f"Role: {role}.")
    explanation = llm_row.get("rankingExplanation")
    if explanation:
        parts.append(str(explanation))
    gaps = llm_row.get("skillGaps") or []
    if gaps:
        parts.append(f"Gaps: {', '.join(gaps[:5])}.")
    return " ".join(parts)


def enrich_and_rank_jobs(
    jobs: List[Dict[str, Any]],
    profile: Dict[str, Any],
    search_config: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], MatchPipeline]:
    if not jobs:
        return [], {
            "steps": [
                "scrape_portals",
                "parse_cv_profile",
                "filter_jobs",
                "embedding_similarity",
                "rank_results",
            ],
            "llmUsed": False,
            "embeddingsUsed": False,
            "matchSource": "none",
            "message": (
                "No jobs to rank. Add a LinkedIn portal in Portals, set APIFY_API_TOKEN for live "
                "LinkedIn scraping (https://apify.com/api/job-scraping-api), then run Search or Auto apply."
            ),
        }

    target_role = (
        (search_config.get("titles") or [None])[0]
        or (profile.get("jobTitles") or [None])[0]
        or "Software Engineer"
    )

    embed_status = get_embedding_status()
    enriched: List[Dict[str, Any]] = []
    for job in jobs:
        score, insight, source = _embedding_job_score(profile, job)
        enriched.append(
            {
                **job,
                "match": score,
                "matchSource": source,
                "matchInsight": insight,
                "embeddingScore": score,
            }
        )

    enriched.sort(key=lambda row: row.get("match", 0), reverse=True)

    llm_explanations, llm_meta = _llm_explain_jobs(profile, enriched, target_role)
    llm_meta_block = llm_explanations.pop("__meta__", None) or llm_meta
    llm_used = bool(llm_explanations) and llm_meta.get("status") == "ok"

    if llm_used:
        for job in enriched:
            llm_row = llm_explanations.get(job["id"])
            if not llm_row:
                continue
            job["matchSource"] = "embeddings+llm"
            job["matchInsight"] = _format_llm_insight(job.get("matchInsight", ""), llm_row)
            job["roleClassification"] = llm_row.get("roleClassification")
            job["skillGaps"] = llm_row.get("skillGaps") or []

    if llm_used:
        match_source = "embeddings+llm"
        message = (
            f"Ranked {len(enriched)} job(s) using embedding similarity + "
            f"{llm_meta.get('provider', 'llm')} reasoning."
        )
    elif embed_status.get("available"):
        match_source = "embeddings"
        if llm_available():
            message = (
                f"Ranked {len(enriched)} job(s) using open-source embeddings "
                f"({embed_status.get('model', embedding_model_name())})."
            )
        else:
            message = (
                f"Ranked using embeddings ({embed_status.get('model', embedding_model_name())}). "
                "Start Ollama (USE_LOCAL_LLM=true) or set OPENAI_API_KEY for ranking explanations."
            )
    else:
        match_source = "ml"
        message = (
            "Embedding backends unavailable; used keyword/TF-IDF heuristic fallback. "
            f"{embed_status.get('error', '')}"
        )

    pipeline: MatchPipeline = {
        "steps": [
            "scrape_portals",
            "parse_cv_profile",
            "filter_jobs",
            "embedding_similarity",
            "llm_reasoning",
            "rank_results",
        ],
        "llmUsed": llm_used,
        "embeddingsUsed": bool(embed_status.get("available")),
        "embeddingModel": embed_status.get("model"),
        "llmProvider": llm_meta.get("provider") if llm_used else (llm_meta_block or {}).get("provider"),
        "matchSource": match_source,
        "targetRole": target_role,
        "cvSkillCount": len(profile.get("resumeSkills") or []),
        "message": message,
    }
    return enriched, pipeline
