"""Functional API tests — LinkedIn discovery (LI-* / FUNCTIONAL_TEST_CASES.md)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.linkedin


class TestLinkedInWorkspace:
    def test_workspace_stats(self, client, user_headers):
        response = client.get("/api/linkedin/workspace", headers=user_headers)
        assert response.status_code == 200
        body = response.json()
        stats = body["stats"]
        assert "recruitersFound" in stats
        assert "contacted" in stats
        assert all("bookmarked" in recruiter for recruiter in body["recruiters"])


class TestLinkedInDiscover:
    def test_discover_empty_companies_returns_all(self, client, user_headers):
        response = client.post(
            "/api/linkedin/discover",
            headers=user_headers,
            json={
                "companies": [],
                "technologies": ["Java"],
                "seniority": "Any",
                "location": "United States",
                "connections": "Any",
                "resultsPerCompany": 5,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert "recruiters" in body

    def test_discover_success(self, client, user_headers):
        response = client.post(
            "/api/linkedin/discover",
            headers=user_headers,
            json={
                "companies": ["TEKsystems", "Infosys"],
                "technologies": ["Java", "Spring Boot"],
                "seniority": "Any",
                "location": "United States",
                "connections": "Any",
                "resultsPerCompany": 5,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert "recruiters" in body
        assert isinstance(body["recruiters"], list)


class TestLinkedInEnrich:
    def test_enrich_urls(self, client, user_headers):
        response = client.post(
            "/api/linkedin/enrich",
            headers=user_headers,
            json={
                "urls": [
                    "https://www.linkedin.com/in/example-recruiter-1",
                    "https://www.linkedin.com/in/example-recruiter-2",
                ],
                "techContext": "Java",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert "profiles" in body
        assert isinstance(body["profiles"], list)


class TestLinkedInOutreach:
    def test_generate_message(self, client, user_headers):
        response = client.post(
            "/api/linkedin/outreach/generate",
            headers=user_headers,
            json={
                "prompt": "Write a connection request for a Java developer available C2C",
                "messageType": "connect",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body.get("subject") or body.get("body")

    def test_schedule_outreach_for_future(self, client, admin_headers):
        workspace = client.get("/api/linkedin/workspace", headers=admin_headers).json()
        recruiters = workspace.get("recruiters") or []
        if not recruiters:
            pytest.skip("No recruiter seed data")
        response = client.post(
            "/api/linkedin/outreach",
            headers=admin_headers,
            json={
                "recruiterIds": [recruiters[0]["id"]],
                "subject": "Scheduled recruiter outreach",
                "body": "<p>Hello recruiter</p>",
                "channel": "LinkedIn Message",
                "scheduleAt": "2099-01-01T09:00:00Z",
            },
        )
        assert response.status_code == 200
        assert "scheduled" in response.json()["message"].lower()

    def test_rejects_past_outreach_schedule(self, client, admin_headers):
        response = client.post(
            "/api/linkedin/outreach",
            headers=admin_headers,
            json={
                "recruiterIds": [1],
                "subject": "Past outreach",
                "body": "<p>Hello recruiter</p>",
                "channel": "LinkedIn Message",
                "scheduleAt": "2020-01-01T09:00:00Z",
            },
        )
        assert response.status_code == 422


class TestLinkedInSavedItems:
    def test_bookmark_recruiter_persists(self, client, admin_headers):
        workspace = client.get("/api/linkedin/workspace", headers=admin_headers).json()
        recruiters = workspace.get("recruiters") or []
        if not recruiters:
            pytest.skip("No recruiter seed data")
        recruiter_id = recruiters[0]["id"]
        response = client.put(
            f"/api/linkedin/recruiters/{recruiter_id}/bookmark",
            headers=admin_headers,
            json={"bookmarked": True},
        )
        assert response.status_code == 200
        refreshed = client.get("/api/linkedin/workspace", headers=admin_headers).json()
        saved = next(row for row in refreshed["recruiters"] if row["id"] == recruiter_id)
        assert saved["bookmarked"] is True

    def test_save_template_persists(self, client, admin_headers):
        response = client.post(
            "/api/linkedin/templates",
            headers=admin_headers,
            json={"name": "Functional Test Template", "body": "<p>Hello {{recruiter_name}}</p>"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Functional Test Template"
        workspace = client.get("/api/linkedin/workspace", headers=admin_headers).json()
        assert any(row["name"] == "Functional Test Template" for row in workspace["templates"])
