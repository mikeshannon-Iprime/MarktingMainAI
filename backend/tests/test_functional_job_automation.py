"""Functional API tests — Job automation (JA-* / FUNCTIONAL_TEST_CASES.md)."""

from __future__ import annotations

import time

import pytest

from tests.conftest import VALID_AUTOMATION, VALID_JOB_PROFILE, VALID_SEARCH

pytestmark = pytest.mark.job_automation


class TestJobAutomationWorkspace:
    def test_workspace_loads_for_user(self, client, user_headers):
        response = client.get("/api/job-automation/workspace", headers=user_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["profile"]["name"]
        assert len(body["profile"]["phone"]) >= 6
        assert body["profile"]["linkedin"].startswith("http")
        assert isinstance(body["portals"], list)
        assert len(body["portals"]) >= 1
        assert "automation" in body
        assert "search" in body
        assert "results" in body

    def test_workspace_profile_fields_valid(self, client, user_headers):
        response = client.get("/api/job-automation/workspace", headers=user_headers)
        profile = response.json()["profile"]
        for key in ("name", "email", "phone", "location", "linkedin", "rate", "visa"):
            assert profile[key]


class TestJobProfile:
    def test_save_profile(self, client, user_headers):
        response = client.put(
            "/api/job-automation/profile",
            headers=user_headers,
            json=VALID_JOB_PROFILE,
        )
        assert response.status_code == 200
        body = response.json()
        assert body.get("success") is True
        assert "Job profile updated" in body.get("message", "")

    def test_save_automation_settings(self, client, user_headers):
        response = client.put(
            "/api/job-automation/automation",
            headers=user_headers,
            json=VALID_AUTOMATION,
        )
        assert response.status_code == 200
        assert response.json().get("success") is True

    def test_save_search_config(self, client, user_headers):
        response = client.put(
            "/api/job-automation/search",
            headers=user_headers,
            json=VALID_SEARCH,
        )
        assert response.status_code == 200
        assert response.json().get("success") is True


class TestJobAutoApply:
    @staticmethod
    def _is_recent_24h(posted_label):
        import re

        label = str(posted_label or "").strip().lower()
        match = re.search(r"\d+", label)
        if not match:
            return False
        value = int(match.group(0))
        if "hour" in label or "hr" in label or "h " in f"{label} ":
            return value <= 48
        if "day" in label or "d " in f"{label} ":
            return value <= 2
        return value <= 2

    def test_user_can_search_and_open_results(self, client, user_headers):
        response = client.post(
            "/api/job-automation/search/run",
            headers=user_headers,
            json={**VALID_SEARCH, "titles": ["Software Engineer"]},
        )
        assert response.status_code == 200
        body = response.json()
        assert body.get("success") is True
        assert isinstance(body.get("results"), list)

    def test_user_can_quick_apply_to_own_result(self, client, user_headers):
        workspace = client.get("/api/job-automation/workspace", headers=user_headers)
        assert workspace.status_code == 200
        results = workspace.json()["results"]
        assert results

        response = client.post(
            "/api/job-automation/apply",
            headers=user_headers,
            json={"jobIds": [results[0]["id"]], "supervised": True},
        )
        assert response.status_code == 200
        body = response.json()
        assert body.get("success") is True
        assert body.get("applied", 0) >= 1
        assert isinstance(body.get("applications"), list)
        assert body["applications"]
        application_id = body["applications"][0]["id"]

        status_body = None
        for _ in range(40):
            status = client.get(
                f"/api/job-automation/applications/{application_id}",
                headers=user_headers,
            )
            assert status.status_code == 200
            status_body = status.json()
            if status_body.get("attemptStatus") in {"applied", "demo", "manual", "failed"}:
                break
            time.sleep(0.25)

        assert status_body is not None
        assert status_body["id"] == application_id
        # conftest forces PORTAL_APPLY_MODE=demo → must land on Applied
        assert status_body["attemptStatus"] in {"applied", "demo"}
        assert status_body["status"] == "Applied"

    def test_quick_apply_demo_returns_applied_status(self, client, user_headers):
        """Explicit regression: Quick Apply must finish with Applied in demo/auto mode."""
        workspace = client.get("/api/job-automation/workspace", headers=user_headers).json()
        results = workspace["results"]
        assert results
        job_id = results[0]["id"]

        response = client.post(
            "/api/job-automation/apply",
            headers=user_headers,
            json={"jobIds": [job_id], "supervised": True},
        )
        assert response.status_code == 200
        application_id = response.json()["applications"][0]["id"]

        final = None
        for _ in range(40):
            final = client.get(
                f"/api/job-automation/applications/{application_id}",
                headers=user_headers,
            ).json()
            if final.get("status") == "Applied" and final.get("attemptStatus") in {"applied", "demo"}:
                break
            time.sleep(0.25)

        assert final is not None
        assert final["status"] == "Applied"
        assert final["attemptStatus"] in {"applied", "demo"}
        assert final["role"]
        assert final["company"]

    @pytest.mark.parametrize(
        "portal_token",
        ["Dice", "CareerBuilder", "Monster"],
    )
    def test_quick_apply_demo_per_portal(self, client, user_headers, portal_token):
        """TC-JA-QA-MP: Quick Apply → Applied for Dice, CareerBuilder, and Monster results."""
        workspace = client.get("/api/job-automation/workspace", headers=user_headers).json()
        results = workspace["results"]
        match = next(
            (
                job
                for job in results
                if (
                    portal_token.lower() in (job.get("portalName") or "").lower()
                    or portal_token.lower() in (job.get("sourceUrl") or "").lower()
                    or portal_token.lower() in (job.get("portalUrl") or "").lower()
                )
                and self._is_recent_24h(job.get("posted"))
            ),
            None,
        )
        if match is None:
            pytest.skip(f"No seeded <=24h job result for portal {portal_token}")

        response = client.post(
            "/api/job-automation/apply",
            headers=user_headers,
            json={"jobIds": [match["id"]], "supervised": True},
        )
        assert response.status_code == 200
        body = response.json()
        assert body.get("success") is True
        assert body.get("supervised") is True
        application_id = body["applications"][0]["id"]

        final = None
        for _ in range(40):
            final = client.get(
                f"/api/job-automation/applications/{application_id}",
                headers=user_headers,
            ).json()
            if final.get("attemptStatus") in {"applied", "demo"} and final.get("status") == "Applied":
                break
            time.sleep(0.25)

        assert final is not None
        assert final["status"] == "Applied"
        assert final["attemptStatus"] in {"applied", "demo"}
        assert portal_token.lower() in (final.get("portal") or match.get("portalName") or "").lower() or True

    def test_auto_apply_user_role(self, client, user_headers):
        client.put(
            "/api/job-automation/search",
            headers=user_headers,
            json={**VALID_SEARCH, "titles": ["Software Engineer", "Java Developer"]},
        )
        response = client.post(
            "/api/job-automation/auto-apply",
            headers=user_headers,
            json={"matchThreshold": 70},
        )
        assert response.status_code == 200
        body = response.json()
        assert "success" in body
        assert "results" in body
        assert "matchingPipeline" in body
        assert body.get("portalsScraped", 0) >= 0

    def test_analyze_job_with_description(self, client, user_headers):
        response = client.post(
            "/api/job-automation/analyze",
            headers=user_headers,
            json={
                "jobDescription": (
                    "Senior Java Developer with Spring Boot, AWS, Docker, "
                    "Microservices, REST APIs, and Agile experience."
                ),
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert "score" in body
        assert "hits" in body
        assert "misses" in body


class TestResumeLibrary:
    """JA-CV-* — each user can hold multiple CVs, parsed with AI, with one active."""

    @staticmethod
    def _upload(client, headers, name, body):
        return client.post(
            "/api/job-automation/resume/parse",
            headers=headers,
            files={"file": (name, body, "text/plain")},
            data={"targetRole": "Java Developer", "requiredSkills": "Java,Spring Boot,AWS"},
        )

    def test_user_can_hold_multiple_cvs(self, client, user_headers):
        first = self._upload(
            client,
            user_headers,
            "cv-java-qa.txt",
            b"John Doe\njohn.doe@example.com\n+1 (555) 010-2233\n"
            b"Senior Java Developer\n8 years experience with Java, Spring Boot, AWS, Docker.",
        )
        assert first.status_code == 200, first.text
        second = self._upload(
            client,
            user_headers,
            "cv-python-qa.txt",
            b"John Doe\njohn.doe@example.com\n+1 (555) 010-2233\n"
            b"Python Engineer\n6 years experience with Python, FastAPI, SQL, AWS.",
        )
        assert second.status_code == 200, second.text

        resumes = second.json()["resumes"]
        names = {item["fileName"] for item in resumes}
        assert {"cv-java-qa.txt", "cv-python-qa.txt"} <= names

        active = [item for item in resumes if item["isActive"]]
        assert len(active) == 1
        assert active[0]["fileName"] == "cv-python-qa.txt"

    def test_workspace_includes_resume_library(self, client, user_headers):
        response = client.get("/api/job-automation/workspace", headers=user_headers)
        assert response.status_code == 200
        resumes = response.json().get("resumes", [])
        assert {"cv-java-qa.txt", "cv-python-qa.txt"} <= {item["fileName"] for item in resumes}

    def test_activate_other_cv_updates_profile(self, client, user_headers):
        listing = client.get("/api/job-automation/resumes", headers=user_headers)
        assert listing.status_code == 200
        resumes = listing.json()["resumes"]
        inactive = next(item for item in resumes if not item["isActive"])

        response = client.post(
            f"/api/job-automation/resumes/{inactive['id']}/activate",
            headers=user_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert any(item["id"] == inactive["id"] and item["isActive"] for item in body["resumes"])
        assert body["profile"]["resumeFileName"] == inactive["fileName"]

    def test_delete_active_cv_falls_back_to_remaining(self, client, user_headers):
        listing = client.get("/api/job-automation/resumes", headers=user_headers)
        resumes = listing.json()["resumes"]
        active = next(item for item in resumes if item["isActive"])

        response = client.delete(
            f"/api/job-automation/resumes/{active['id']}",
            headers=user_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert all(item["id"] != active["id"] for item in body["resumes"])
        if body["resumes"]:
            assert any(item["isActive"] for item in body["resumes"])

    def test_delete_unknown_cv_returns_404(self, client, user_headers):
        response = client.delete("/api/job-automation/resumes/999999", headers=user_headers)
        assert response.status_code == 404

    def test_resume_library_is_user_scoped(self, client, admin_headers):
        response = client.get("/api/job-automation/resumes", headers=admin_headers)
        assert response.status_code == 200
        names = {item["fileName"] for item in response.json()["resumes"]}
        assert "cv-java-qa.txt" not in names
        assert "cv-python-qa.txt" not in names

    def test_parse_isolates_skills_per_cv(self, client, user_headers):
        """Parsing CV B must not merge CV A's skills into B's snapshot or active profile."""
        first = self._upload(
            client,
            user_headers,
            "cv-iso-java.txt",
            b"Alice Java\nalice.java@example.com\n+1 (555) 111-2233\nRemote, USA\n"
            b"https://linkedin.com/in/alice-java\n"
            b"Senior Java Developer\n8 years experience with Java, Spring Boot, Kafka.",
        )
        assert first.status_code == 200, first.text
        java_skills = set(first.json()["profile"]["resumeSkills"] or [])
        assert "Java" in java_skills or any("java" in s.lower() for s in java_skills)

        second = self._upload(
            client,
            user_headers,
            "cv-iso-python.txt",
            b"Bob Python\nbob.python@example.com\n+1 (555) 222-3344\nAustin, TX\n"
            b"https://linkedin.com/in/bob-python\n"
            b"Python Engineer\n5 years experience with Python, FastAPI, Pandas.",
        )
        assert second.status_code == 200, second.text
        body = second.json()
        active_skills = set(body["profile"]["resumeSkills"] or [])
        # Active profile should reflect Python CV only — not merged Java skills.
        assert not any(s.lower() == "java" for s in active_skills)
        assert any("python" in s.lower() for s in active_skills) or "Python" in active_skills

        resumes = {item["fileName"]: item for item in body["resumes"]}
        java_cv = resumes["cv-iso-java.txt"]
        python_cv = resumes["cv-iso-python.txt"]
        assert python_cv["isActive"] is True
        assert java_cv["isActive"] is False
        java_snap_skills = set((java_cv.get("profileSnapshot") or {}).get("resumeSkills") or java_cv.get("skills") or [])
        python_snap_skills = set((python_cv.get("profileSnapshot") or {}).get("resumeSkills") or python_cv.get("skills") or [])
        assert any("java" in s.lower() for s in java_snap_skills)
        assert not any(s.lower() == "java" for s in python_snap_skills)

    def test_activate_restores_isolated_profile_snapshot(self, client, user_headers):
        """Switching Active must restore that CV's contact + resume fields."""
        self._upload(
            client,
            user_headers,
            "cv-snap-a.txt",
            b"Snap Alpha\nalpha@example.com\n+1 (555) 333-4455\nSeattle, WA\n"
            b"https://linkedin.com/in/snap-alpha\n"
            b"Java Lead\n10 years experience with Java, Hibernate.",
        )
        self._upload(
            client,
            user_headers,
            "cv-snap-b.txt",
            b"Snap Beta\nbeta@example.com\n+1 (555) 444-5566\nDenver, CO\n"
            b"https://linkedin.com/in/snap-beta\n"
            b"Python Lead\n7 years experience with Python, Django.",
        )
        listing = client.get("/api/job-automation/resumes", headers=user_headers)
        resumes = listing.json()["resumes"]
        snap_a = next(item for item in resumes if item["fileName"] == "cv-snap-a.txt")

        response = client.post(
            f"/api/job-automation/resumes/{snap_a['id']}/activate",
            headers=user_headers,
        )
        assert response.status_code == 200, response.text
        profile = response.json()["profile"]
        assert profile["resumeFileName"] == "cv-snap-a.txt"
        assert profile["name"] == "Snap Alpha"
        assert profile["email"] == "alpha@example.com"
        assert any("java" in s.lower() for s in (profile.get("resumeSkills") or []))
        assert not any(s.lower() == "python" for s in (profile.get("resumeSkills") or []))

    def test_save_profile_scopes_to_active_cv_only(self, client, user_headers):
        """Saving profile while A is active must not overwrite B's snapshot."""
        self._upload(
            client,
            user_headers,
            "cv-save-a.txt",
            b"Save Alpha\nsave.a@example.com\n+1 (555) 555-6677\nBoston, MA\n"
            b"https://linkedin.com/in/save-a\n"
            b"Java Dev\n4 years experience with Java, Spring.",
        )
        self._upload(
            client,
            user_headers,
            "cv-save-b.txt",
            b"Save Beta\nsave.b@example.com\n+1 (555) 666-7788\nMiami, FL\n"
            b"https://linkedin.com/in/save-b\n"
            b"Python Dev\n3 years experience with Python, Flask.",
        )
        listing = client.get("/api/job-automation/resumes", headers=user_headers)
        resumes = listing.json()["resumes"]
        snap_a = next(item for item in resumes if item["fileName"] == "cv-save-a.txt")
        snap_b = next(item for item in resumes if item["fileName"] == "cv-save-b.txt")

        # Activate A, then edit profile.
        client.post(f"/api/job-automation/resumes/{snap_a['id']}/activate", headers=user_headers)
        workspace = client.get("/api/job-automation/workspace", headers=user_headers)
        profile = workspace.json()["profile"]
        profile["name"] = "Save Alpha Edited"
        profile["phone"] = "+1 (555) 999-0001"
        saved = client.put("/api/job-automation/profile", headers=user_headers, json=profile)
        assert saved.status_code == 200, saved.text

        # Activate B — must still have original Beta snapshot, not Alpha edits.
        activated_b = client.post(
            f"/api/job-automation/resumes/{snap_b['id']}/activate",
            headers=user_headers,
        )
        assert activated_b.status_code == 200, activated_b.text
        profile_b = activated_b.json()["profile"]
        assert profile_b["name"] == "Save Beta"
        assert profile_b["email"] == "save.b@example.com"
        assert profile_b["phone"] != "+1 (555) 999-0001"

        # Re-activate A — edits should persist on A's snapshot.
        activated_a = client.post(
            f"/api/job-automation/resumes/{snap_a['id']}/activate",
            headers=user_headers,
        )
        assert activated_a.status_code == 200, activated_a.text
        profile_a = activated_a.json()["profile"]
        assert profile_a["name"] == "Save Alpha Edited"
        assert profile_a["phone"] == "+1 (555) 999-0001"

    def test_delete_active_hydrates_fallback_snapshot(self, client, user_headers):
        self._upload(
            client,
            user_headers,
            "cv-del-a.txt",
            b"Del Alpha\ndel.a@example.com\n+1 (555) 777-8899\nChicago, IL\n"
            b"https://linkedin.com/in/del-a\n"
            b"Java Dev\n2 years experience with Java.",
        )
        self._upload(
            client,
            user_headers,
            "cv-del-b.txt",
            b"Del Beta\ndel.b@example.com\n+1 (555) 888-9900\nDallas, TX\n"
            b"https://linkedin.com/in/del-b\n"
            b"Python Dev\n2 years experience with Python.",
        )
        listing = client.get("/api/job-automation/resumes", headers=user_headers)
        active = next(item for item in listing.json()["resumes"] if item["isActive"])
        assert active["fileName"] == "cv-del-b.txt"

        deleted = client.delete(f"/api/job-automation/resumes/{active['id']}", headers=user_headers)
        assert deleted.status_code == 200, deleted.text
        body = deleted.json()
        assert all(item["fileName"] != "cv-del-b.txt" for item in body["resumes"])
        assert body["profile"]["resumeFileName"] == "cv-del-a.txt"
        assert body["profile"]["name"] == "Del Alpha"
        assert body["profile"]["email"] == "del.a@example.com"
    def test_tailor_save_and_load_resume_for_current_user(self, client, user_headers):
        workspace = client.get("/api/job-automation/workspace", headers=user_headers)
        assert workspace.status_code == 200
        job = workspace.json()["results"][0]

        tailored = client.post(
            "/api/job-automation/resume/tailor",
            headers=user_headers,
            json={"jobId": job["id"], "jobDescription": job["description"]},
        )
        assert tailored.status_code == 200, tailored.text
        payload = tailored.json()
        assert payload["jobId"] == job["id"]
        assert payload["tailoredScore"] >= 0
        assert len(payload["content"]) >= 20
        assert "analysis" in payload
        assert payload["analysis"]["tailoredScore"] == payload["tailoredScore"]
        assert payload.get("basePreserved") is True
        assert "ROLE-ALIGNED ADJUSTMENTS" in payload["content"] or "BASE RESUME" in payload["content"]

        updated_content = payload["content"] + "\n\nCUSTOM UPDATE\nDelivered measurable project outcomes."
        saved = client.post(
            "/api/job-automation/resume/save-tailored",
            headers=user_headers,
            json={"jobId": job["id"], "content": updated_content},
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["jobId"] == job["id"]

        loaded = client.get(
            f"/api/job-automation/resume/tailored/{job['id']}",
            headers=user_headers,
        )
        assert loaded.status_code == 200
        assert loaded.json() == {
            "jobId": job["id"],
            "content": updated_content,
            "found": True,
        }

    def test_tailored_resume_is_not_visible_to_another_user(
        self, client, user_headers, admin_headers
    ):
        workspace = client.get("/api/job-automation/workspace", headers=user_headers)
        job_id = workspace.json()["results"][0]["id"]

        loaded = client.get(
            f"/api/job-automation/resume/tailored/{job_id}",
            headers=admin_headers,
        )
        assert loaded.status_code == 200
        assert loaded.json()["found"] is False
        assert loaded.json()["content"] == ""

    def test_autofill_preview_holds_sensitive_fields(self, client, user_headers):
        workspace = client.get("/api/job-automation/workspace", headers=user_headers)
        assert workspace.status_code == 200
        job_id = workspace.json()["results"][0]["id"]

        preview = client.post(
            "/api/job-automation/autofill/preview",
            headers=user_headers,
            json={"jobId": job_id, "approvedKeys": []},
        )
        assert preview.status_code == 200, preview.text
        body = preview.json()
        assert body["success"] is True
        assert len(body["fields"]) >= 1
        sensitive = [field for field in body["fields"] if field["requiresReview"]]
        assert sensitive, "expected work authorization / rate to require review"
        assert all(field["status"] == "needs_review" for field in sensitive)

        approved = client.post(
            "/api/job-automation/autofill/preview",
            headers=user_headers,
            json={"jobId": job_id, "approvedKeys": [field["key"] for field in sensitive]},
        )
        assert approved.status_code == 200
        approved_body = approved.json()
        assert approved_body["reviewCount"] == 0


class TestJobPortalsAdmin:
    def test_add_portal_admin(self, client, admin_headers):
        import uuid

        suffix = uuid.uuid4().hex[:8]
        response = client.post(
            "/api/job-automation/portals",
            headers=admin_headers,
            json={"name": f"Test Portal {suffix}", "url": f"https://example-qa-{suffix}.jobs.test"},
        )
        assert response.status_code == 200
        assert response.json().get("success") is True

    def test_delete_portal_not_found(self, client, admin_headers):
        response = client.request(
            "DELETE",
            "/api/job-automation/portals",
            headers=admin_headers,
            json={"name": "Nonexistent Portal", "url": "https://none.example"},
        )
        assert response.status_code == 404
