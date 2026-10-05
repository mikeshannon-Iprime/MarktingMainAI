"""Functional API tests — Auth & workspace load (FUNCTIONAL_TEST_CASES.md)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.auth


class TestAuth:
    def test_auth_options(self, client):
        response = client.get("/api/auth/options")
        assert response.status_code == 200
        body = response.json()
        assert "roles" in body

    def test_login_user_success(self, client):
        response = client.post(
            "/api/auth/login",
            json={"email": "user@marketingmind.ai", "password": "User@123"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["token"]
        assert body["user"]["email"] == "user@marketingmind.ai"
        assert body["user"]["role"] == "user"

    def test_login_invalid_password(self, client):
        response = client.post(
            "/api/auth/login",
            json={"email": "user@marketingmind.ai", "password": "wrongpw"},
        )
        assert response.status_code == 401

    def test_me_requires_auth(self, client):
        assert client.get("/api/auth/me").status_code == 401

    def test_me_authenticated(self, client, user_headers):
        response = client.get("/api/auth/me", headers=user_headers)
        assert response.status_code == 200
        assert response.json()["user"]["email"] == "user@marketingmind.ai"


class TestWorkspaceLoad:
    def test_overview(self, client, user_headers):
        response = client.get("/api/overview", headers=user_headers)
        assert response.status_code == 200
        body = response.json()
        assert "modules" in body
        assert len(body["modules"]) >= 1

    def test_campaigns_workspace(self, client, user_headers):
        response = client.get("/api/campaigns/workspace", headers=user_headers)
        assert response.status_code == 200
        body = response.json()
        assert "contacts" in body
        assert "templates" in body

    def test_day_report_dashboard(self, client, user_headers):
        response = client.get("/api/day-report/dashboard", headers=user_headers)
        assert response.status_code == 200
        body = response.json()
        assert "rows" in body
        assert "totals" in body
        assert "range" in body

    def test_submissions_dashboard(self, client, user_headers):
        response = client.get("/api/submissions/dashboard", headers=user_headers)
        assert response.status_code == 200
        body = response.json()
        assert "months" in body
        assert "summary" in body
        assert "range" in body

    def test_linkedin_workspace(self, client, user_headers):
        response = client.get("/api/linkedin/workspace", headers=user_headers)
        assert response.status_code == 200
        body = response.json()
        assert "recruiters" in body
        assert "stats" in body
