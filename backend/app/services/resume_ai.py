from __future__ import annotations

import asyncio
import json
import os
import re
from io import BytesIO
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, UploadFile

from app.core.config import get_settings
from app.services.llm_client import invoke_llm, llm_available

COMMON_SKILLS = {
    "python",
    "java",
    "javascript",
    "typescript",
    "spring boot",
    "spring",
    "sql",
    "postgresql",
    "mysql",
    "mongodb",
    "fastapi",
    "django",
    "flask",
    "react",
    "angular",
    "vue",
    "node.js",
    "node",
    "aws",
    "azure",
    "gcp",
    "docker",
    "kubernetes",
    "kafka",
    "redis",
    "graphql",
    "rest",
    "microservices",
    "agile",
    "scrum",
    "git",
    "jenkins",
    "terraform",
    "ansible",
    "hadoop",
    "spark",
    "scala",
    "go",
    "golang",
    "c#",
    ".net",
    "machine learning",
    "deep learning",
    "llm",
    "langchain",
    "pandas",
    "numpy",
    "tensorflow",
    "pytorch",
}

EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}")
EXPERIENCE_REGEX = re.compile(r"(\d+(?:\.\d+)?)\+?\s+years?", re.IGNORECASE)
LINKEDIN_REGEX = re.compile(
    r"(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9_-]+/?",
    re.IGNORECASE,
)
NAME_LABEL_REGEX = re.compile(
    r"(?i)\b(?:name|full\s*name)\s*[:\-]\s*([A-Za-z][A-Za-z .'-]{1,80})",
)
LOCATION_LABEL_REGEX = re.compile(
    r"(?i)\b(?:location|address|based\s*in|city)\s*[:\-]\s*([^\n|;]{2,80})",
)
HEADER_NOISE = re.compile(
    r"(?i)^(curriculum\s+vitae|resume|cv|profile|contact|personal\s+details?)\s*$",
)
TITLE_TRAILING = re.compile(
    r"(?i)\s+(?:sr\.?|senior|junior|lead|principal|staff)?\s*"
    r"(?:java|python|\.net|full[\s-]?stack|software|data|cloud|ai|ml)?\s*"
    r"(?:developer|engineer|architect|analyst|consultant|manager|specialist)\b.*$",
)


async def parse_resume_with_ai(
    file: UploadFile,
    target_role: str,
    required_skills: List[str],
) -> Dict[str, Any]:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded resume file is empty.")

    text = _extract_text(file.filename or "resume.txt", content)
    cleaned_text = _normalize_text(text)

    parsed_profile = _rule_based_profile_parse(cleaned_text)
    ml_assessment = _ml_skill_assessment(cleaned_text, target_role, required_skills)

    settings = get_settings()
    include_llm = settings.resume_parse_include_llm or llm_available()
    llm_budget = settings.resume_parse_llm_timeout_seconds + 2

    if include_llm:
        try:
            llm_assessment, agent_trace = await asyncio.wait_for(
                asyncio.to_thread(
                    _langchain_agent_assessment,
                    cleaned_text,
                    target_role,
                    required_skills,
                ),
                timeout=llm_budget,
            )
        except asyncio.TimeoutError:
            llm_assessment = {
                "usedLangChain": False,
                "provider": "ollama" if settings.use_local_llm else "none",
                "model": settings.ollama_model if settings.use_local_llm else "none",
                "status": "timeout",
                "insights": (
                    f"LLM reasoning timed out after {settings.resume_parse_llm_timeout_seconds}s. "
                    "Structured parsing and ML skill scoring completed successfully."
                ),
            }
            agent_trace = {
                "used": False,
                "mode": "timeout_fallback",
                "steps": [
                    "extract_text",
                    "rule_based_profile_parse",
                    "ml_skill_assessment",
                    "llm_timeout_fallback",
                ],
            }
    else:
        llm_assessment = {
            "usedLangChain": False,
            "provider": "none",
            "model": "none",
            "status": "skipped",
            "insights": (
                "LLM reasoning skipped for fast parse. "
                "Set RESUME_PARSE_INCLUDE_LLM=true in backend/.env when Ollama is ready."
            ),
        }
        agent_trace = {
            "used": False,
            "mode": "llm_disabled",
            "steps": [
                "extract_text",
                "rule_based_profile_parse",
                "ml_skill_assessment",
            ],
        }

    preview = cleaned_text[:400]

    return {
        "filename": file.filename or "resume.txt",
        "contentType": file.content_type or "application/octet-stream",
        "sizeBytes": len(content),
        "extractedTextPreview": preview,
        "parsedProfile": parsed_profile,
        "mlAssessment": ml_assessment,
        "llmAssessment": llm_assessment,
        "agentTrace": agent_trace,
        "_fileBytes": content,
        "_contentType": file.content_type or "application/octet-stream",
    }


def _extract_text(filename: str, content: bytes) -> str:
    lowered = filename.lower()

    if lowered.endswith(".txt"):
        return content.decode("utf-8", errors="ignore")

    if lowered.endswith(".pdf"):
        try:
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(content))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception:
            return content.decode("utf-8", errors="ignore")

    if lowered.endswith(".docx"):
        try:
            from docx import Document

            doc = Document(BytesIO(content))
            return "\n".join(paragraph.text for paragraph in doc.paragraphs)
        except Exception:
            return content.decode("utf-8", errors="ignore")

    return content.decode("utf-8", errors="ignore")


def _normalize_text(text: str) -> str:
    compact = re.sub(r"\r", "\n", text)
    compact = re.sub(r"\n{3,}", "\n\n", compact)
    return compact.strip()


TITLE_HINTS = (
    "developer",
    "engineer",
    "architect",
    "analyst",
    "consultant",
    "manager",
    "lead",
    "administrator",
)


def _extract_skills_from_text(text: str) -> List[str]:
    lowered = text.lower()
    found: List[str] = []
    # Match multi-word skills first (longer phrases take priority).
    for skill in sorted(COMMON_SKILLS, key=len, reverse=True):
        if skill in lowered and skill not in [item.lower() for item in found]:
            label = " ".join(part.capitalize() if part != ".net" else ".NET" for part in skill.split())
            if skill == "spring boot":
                label = "Spring Boot"
            elif skill == "node.js":
                label = "Node.js"
            elif skill == "c#":
                label = "C#"
            found.append(label)

    skills_section = re.search(
        r"(?:skills|technical skills|technologies|competencies)\s*[:\-]?\s*(.+?)(?:\n\n|\n[A-Z][a-z]+:|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if skills_section:
        chunk = skills_section.group(1)
        for token in re.split(r"[,;|•\n/]+", chunk):
            cleaned = token.strip(" -•\t")
            if 2 <= len(cleaned) <= 40 and cleaned.lower() not in {item.lower() for item in found}:
                found.append(cleaned.title() if cleaned.islower() else cleaned)

    return found[:30]


def _extract_job_titles(text: str) -> List[str]:
    titles = []
    for line in text.splitlines():
        cleaned = line.strip()
        if not cleaned or len(cleaned) > 80:
            continue
        lowered = cleaned.lower()
        if any(hint in lowered for hint in TITLE_HINTS):
            formatted = " ".join(word.capitalize() for word in cleaned.split())
            if formatted not in titles:
                titles.append(formatted)
        if len(titles) >= 6:
            break
    return titles


def _collapse_ws(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _looks_like_person_name(value: str) -> bool:
    cleaned = _collapse_ws(value)
    if not cleaned or len(cleaned) < 3 or len(cleaned) > 80:
        return False
    if EMAIL_REGEX.search(cleaned) or PHONE_REGEX.search(cleaned):
        return False
    if HEADER_NOISE.match(cleaned):
        return False
    if any(ch.isdigit() for ch in cleaned):
        return False
    words = cleaned.split()
    if not (2 <= len(words) <= 5):
        return False
    return all(re.fullmatch(r"[A-Za-z][A-Za-z.'-]*", word) for word in words)


def _extract_full_name(text: str, lines: List[str]) -> Optional[str]:
    labeled = NAME_LABEL_REGEX.search(text)
    if labeled:
        candidate = _collapse_ws(labeled.group(1))
        candidate = TITLE_TRAILING.sub("", candidate).strip(" -|,;")
        if _looks_like_person_name(candidate):
            return candidate
        # Label matched but title/noise trailed — keep first 2–4 tokens.
        tokens = [tok for tok in candidate.split() if re.fullmatch(r"[A-Za-z][A-Za-z.'-]*", tok)]
        if 2 <= len(tokens) <= 4:
            return " ".join(tokens)

    for raw in lines[:8]:
        line = _collapse_ws(raw)
        if HEADER_NOISE.match(line):
            continue
        # Word docs often flatten header cells into one long spaced line.
        for chunk in re.split(r"\s{2,}|\||•|;", raw):
            chunk = _collapse_ws(chunk)
            chunk = re.sub(r"(?i)^(name|full\s*name)\s*[:\-]\s*", "", chunk).strip()
            chunk = TITLE_TRAILING.sub("", chunk).strip(" -|,;")
            if _looks_like_person_name(chunk):
                return chunk
        cleaned = re.sub(r"(?i)^(name|full\s*name)\s*[:\-]\s*", "", line).strip()
        cleaned = TITLE_TRAILING.sub("", cleaned).strip(" -|,;")
        if _looks_like_person_name(cleaned):
            return cleaned
    return None


def _extract_location(text: str, lines: List[str]) -> Optional[str]:
    labeled = LOCATION_LABEL_REGEX.search(text)
    if labeled:
        candidate = _collapse_ws(labeled.group(1))
        candidate = EMAIL_REGEX.sub("", candidate)
        candidate = PHONE_REGEX.sub("", candidate)
        candidate = candidate.strip(" -|,;")
        if 2 <= len(candidate) <= 120:
            return candidate[:120]

    for line in lines[:12]:
        cleaned = _collapse_ws(line)
        if EMAIL_REGEX.search(cleaned) or PHONE_REGEX.search(cleaned):
            continue
        if HEADER_NOISE.match(cleaned) or NAME_LABEL_REGEX.search(cleaned):
            continue
        if "," in cleaned and not any(ch.isdigit() for ch in cleaned) and len(cleaned) <= 80:
            return cleaned
        # City ST without comma (e.g. "Seattle WA")
        if re.fullmatch(r"[A-Za-z .'-]+,\s*[A-Za-z]{2,}|[A-Za-z .'-]{2,40}\s+[A-Z]{2}\b", cleaned):
            return cleaned[:120]
    return None


def _extract_linkedin(text: str) -> Optional[str]:
    match = LINKEDIN_REGEX.search(text)
    if not match:
        return None
    url = match.group(0).rstrip("/")
    if not url.lower().startswith("http"):
        url = f"https://{url}"
    return url[:255]


def _rule_based_profile_parse(text: str) -> Dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    full_name = _extract_full_name(text, lines)

    email_match = EMAIL_REGEX.search(text)
    phone_match = PHONE_REGEX.search(text)
    location = _extract_location(text, lines)
    linkedin = _extract_linkedin(text)

    extracted_skills = _extract_skills_from_text(text)
    job_titles = _extract_job_titles(text)

    years_experience = None
    exp_match = EXPERIENCE_REGEX.search(text)
    if exp_match:
        try:
            years_experience = float(exp_match.group(1))
        except ValueError:
            years_experience = None

    summary_bits = []
    for line in lines[:5]:
        collapsed = _collapse_ws(line)
        if collapsed and collapsed not in summary_bits:
            summary_bits.append(collapsed)
    summary = " ".join(summary_bits)[:350]

    return {
        "fullName": (full_name[:120] if full_name else None),
        "email": (email_match.group(0)[:255] if email_match else None),
        "phone": (_collapse_ws(phone_match.group(0))[:40] if phone_match else None),
        "location": (location[:120] if location else None),
        "linkedin": linkedin,
        "skills": extracted_skills,
        "jobTitles": job_titles,
        "yearsExperience": years_experience,
        "summary": summary,
    }


def _ml_skill_assessment(text: str, target_role: str, required_skills: List[str]) -> Dict[str, Any]:
    normalized_required = [skill.strip().lower() for skill in required_skills if skill.strip()]
    normalized_required = list(dict.fromkeys(normalized_required))

    if not normalized_required:
        normalized_required = ["python", "sql", "communication"]

    matched = [skill for skill in normalized_required if skill in text.lower()]
    missing = [skill for skill in normalized_required if skill not in matched]

    model_type = "keyword_overlap"
    score = round((len(matched) / len(normalized_required)) * 100)

    # Optional lightweight ML scoring when sklearn is available.
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        target_profile = f"{target_role} {' '.join(normalized_required)}"
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        matrix = vectorizer.fit_transform([text, target_profile])
        similarity = float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])
        score = max(score, round(similarity * 100))
        model_type = "sklearn_tfidf_cosine"
    except Exception:
        pass

    return {
        "modelType": model_type,
        "targetRole": target_role,
        "matchScore": max(0, min(100, score)),
        "matchedSkills": matched,
        "missingSkills": missing,
    }


def _langchain_agent_assessment(text: str, target_role: str, required_skills: List[str]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    system_prompt = (
        "You are a resume analysis assistant for staffing automation. "
        "Extract skills, classify job-role fit, and identify gaps. "
        "Return valid JSON with keys: insights, strengths, improvements, extractedSkills, roleClassification. "
        "Keep each field concise."
    )
    user_prompt = (
        f"Target role: {target_role}\n"
        f"Required skills: {', '.join(required_skills)}\n"
        f"Resume:\n{text[:12000]}\n"
    )

    raw_content, meta = invoke_llm(
        system_prompt,
        user_prompt,
        timeout_seconds=get_settings().resume_parse_llm_timeout_seconds,
        skip_if_unavailable=True,
    )
    if meta.get("status") != "ok" or not raw_content:
        skip_message = meta.get("message") or (
            "LLM reasoning skipped. Start Ollama (USE_LOCAL_LLM=true) "
            "or set OPENAI_API_KEY in backend/.env."
        )
        status = "timeout" if "timed out" in skip_message.lower() else "fallback"
        return (
            {
                "usedLangChain": False,
                "provider": meta.get("provider", "none"),
                "model": meta.get("model") or "none",
                "status": status,
                "insights": skip_message,
            },
            {
                "used": False,
                "mode": "fallback",
                "steps": [
                    "extract_text",
                    "rule_based_profile_parse",
                    "ml_skill_assessment",
                ],
            },
        )

    try:
        parsed = _safe_parse_json(raw_content)

        if parsed:
            insights = parsed.get("insights") or "Structured analysis generated by LLM reasoning layer."
            strengths = parsed.get("strengths") or []
            improvements = parsed.get("improvements") or []
            extracted = parsed.get("extractedSkills") or []
            role_class = parsed.get("roleClassification") or target_role
            insight_block = (
                f"Role classification: {role_class}\n"
                f"Insights: {insights}\n"
                f"Strengths: {', '.join(strengths) if isinstance(strengths, list) else strengths}\n"
                f"Improvements: {', '.join(improvements) if isinstance(improvements, list) else improvements}"
            )
            if extracted:
                insight_block += f"\nExtracted skills: {', '.join(extracted) if isinstance(extracted, list) else extracted}"
        else:
            insight_block = raw_content[:1200]

        provider = meta.get("provider", "llm")
        return (
            {
                "usedLangChain": True,
                "provider": provider,
                "model": meta.get("model") or "unknown",
                "status": "ok",
                "insights": insight_block,
            },
            {
                "used": True,
                "mode": f"{provider}_reasoning",
                "steps": [
                    "extract_text",
                    "rule_based_profile_parse",
                    "ml_skill_assessment",
                    "llm_skill_extraction",
                    "llm_role_classification",
                    "llm_gap_analysis",
                ],
            },
        )
    except Exception as exc:
        return (
            {
                "usedLangChain": False,
                "provider": meta.get("provider", "llm"),
                "model": meta.get("model") or "unknown",
                "status": "error",
                "insights": f"LLM reasoning failed: {str(exc)}",
            },
            {
                "used": False,
                "mode": "fallback_after_error",
                "steps": [
                    "extract_text",
                    "rule_based_profile_parse",
                    "ml_skill_assessment",
                    "llm_error_fallback",
                ],
            },
        )


def _safe_parse_json(value: str) -> Optional[Dict[str, Any]]:
    cleaned = value.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json\n", "", 1)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
        return None
    except Exception:
        return None
