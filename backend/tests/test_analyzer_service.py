"""Unit tests for Analyzer match / tailor / autofill helpers."""

from app.services.analyzer_service import (
    ADJUSTMENTS_MARKER,
    BASE_RESUME_MARKER,
    apply_adjustment_to_content,
    build_autofill_preview,
    build_match_analysis,
    build_surgical_tailor,
    detect_platform,
)


def test_detect_platform_from_url():
    assert detect_platform({"sourceUrl": "https://www.linkedin.com/jobs/view/1"}) == "LinkedIn"
    assert detect_platform({"portalName": "Indeed Easy Apply"}) == "Indeed"


def test_build_match_analysis_highlights_missing_keywords():
    profile = {
        "name": "Alex Candidate",
        "resumeSkills": ["Python", "React", "AWS"],
        "resumeSummary": "Backend engineer with cloud delivery.",
        "experience": "6 years",
        "jobTitles": ["Software Engineer"],
    }
    job = {
        "id": 42,
        "role": "Full Stack Engineer",
        "company": "Acme",
        "location": "Remote",
        "portalName": "LinkedIn",
        "sourceUrl": "https://www.linkedin.com/jobs/view/42",
        "skills": ["Python", "Kubernetes", "React"],
        "description": "Looking for Python and React. Kubernetes experience preferred.",
        "match": 70,
    }
    result = build_match_analysis(profile=profile, selected_job=job, job_description=job["description"])
    assert result["score"] >= 40
    assert result["platform"] == "LinkedIn"
    assert "Python" in result["hits"] or "React" in result["hits"]
    assert result["misses"] or result["missingKeywords"]
    assert result["matchSource"]


def test_surgical_tailor_preserves_base_resume():
    profile = {"name": "Alex", "email": "a@example.com", "resumeSkills": ["Python", "AWS"]}
    job = {
        "role": "Engineer",
        "company": "Acme",
        "description": (
            "Requirements:\n"
            "- Build and operate Python APIs on AWS for high-traffic services\n"
            "- Collaborate with product teams on microservices delivery\n"
            "- Experience with Kubernetes orchestration preferred\n\n"
            "Benefits:\n- Health insurance"
        ),
    }
    analysis = {
        "score": 72,
        "hits": ["Python", "AWS"],
        "misses": ["Kubernetes"],
        "summary": "Solid fit",
        "jobDescription": job["description"],
    }
    existing = "Alex\na@example.com\n\nPROFESSIONAL SUMMARY\nBuilt APIs for 5 years.\n\nEXPERIENCE\nAcme Corp — 2020-2024"
    tailored = build_surgical_tailor(
        profile=profile,
        selected_job=job,
        analysis=analysis,
        existing_tailored=existing,
    )
    assert BASE_RESUME_MARKER in tailored["content"]
    assert ADJUSTMENTS_MARKER in tailored["content"]
    assert "Built APIs for 5 years." in tailored["content"]
    assert "Acme Corp — 2020-2024" in tailored["content"]
    assert tailored["basePreserved"] is True
    assert any("Kubernetes" in item for item in tailored["adjustments"])
    assert tailored["jdPointers"]
    assert "JD-ALIGNED EXPERIENCE POINTERS" in tailored["content"]
    assert any("Python" in item or "AWS" in item for item in tailored["jdPointers"])


def test_extract_jd_requirements_from_sections():
    from app.services.analyzer_service import extract_jd_requirements

    jd = (
        "Responsibilities:\n"
        "- Design distributed Java microservices for payment workflows\n"
        "- Own CI/CD pipelines and production readiness reviews\n\n"
        "Nice to have:\n- GraphQL"
    )
    reqs = extract_jd_requirements(jd)
    assert any("Java microservices" in item for item in reqs)
    assert any("CI/CD" in item for item in reqs)


def test_apply_adjustment_is_idempotent():
    content = f"{BASE_RESUME_MARKER}\nBody\n\n{ADJUSTMENTS_MARKER} ===\n- Keep history intact\n"
    once = apply_adjustment_to_content(content, "Keep history intact")
    twice = apply_adjustment_to_content(once, "Keep history intact")
    assert once.count("Keep history intact") == 1
    assert twice.count("Keep history intact") == 1


def test_autofill_holds_sensitive_fields_for_review():
    profile = {
        "name": "Alex Candidate",
        "email": "alex@example.com",
        "phone": "+1 555 0100",
        "location": "Austin, TX",
        "visa": "H1B",
        "rate": "$90/hr",
        "resumeSkills": ["Python"],
    }
    preview = build_autofill_preview(profile=profile, selected_job={"id": 7, "role": "Engineer", "company": "Acme", "portalName": "Indeed"})
    assert preview["success"] is True
    assert preview["reviewCount"] >= 1
    visa = next(field for field in preview["fields"] if field["key"] == "visa")
    assert visa["requiresReview"] is True
    assert visa["approved"] is False
    assert visa["status"] == "needs_review"

    approved = build_autofill_preview(profile=profile, selected_job={"id": 7}, approved_keys=["visa", "rate"])
    visa_ok = next(field for field in approved["fields"] if field["key"] == "visa")
    assert visa_ok["approved"] is True
    assert visa_ok["status"] == "approved"
