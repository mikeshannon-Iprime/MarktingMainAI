"""Functional API tests — Submissions MoM/YoY (SP-* / FUNCTIONAL_TEST_CASES.md)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.submissions


class TestSubmissionDashboard:
    def test_dashboard_load(self, client, user_headers):
        response = client.get("/api/submissions/dashboard", headers=user_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["summary"]["total"] >= 0
        assert body["summary"]["average"] >= 0
        assert isinstance(body["months"], list)

    def test_filter_full_range(self, client, user_headers):
        dashboard = client.get("/api/submissions/dashboard", headers=user_headers).json()
        if not dashboard["months"]:
            pytest.skip("No submission months in database")
        start = dashboard["range"]["start"]
        end = dashboard["range"]["end"]
        response = client.post(
            "/api/submissions/filter",
            headers=user_headers,
            json={"startMonth": start, "endMonth": end},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["summary"]["total"] == dashboard["summary"]["total"]
        assert len(body["months"]) == len(dashboard["months"])

    def test_filter_single_month(self, client, user_headers):
        dashboard = client.get("/api/submissions/dashboard", headers=user_headers).json()
        if not dashboard["months"]:
            pytest.skip("No submission months in database")
        month = dashboard["months"][0]["month"]
        response = client.post(
            "/api/submissions/filter",
            headers=user_headers,
            json={"startMonth": month, "endMonth": month},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["months"]) == 1
        assert body["months"][0]["month"] == month
        assert body["summary"]["total"] == body["months"][0]["submissions"]

    def test_filter_invalid_range_rejected(self, client, user_headers):
        response = client.post(
            "/api/submissions/filter",
            headers=user_headers,
            json={"startMonth": "2026-05", "endMonth": "2026-01"},
        )
        assert response.status_code == 422

    def test_mom_field_present(self, client, user_headers):
        dashboard = client.get("/api/submissions/dashboard", headers=user_headers).json()
        if len(dashboard["months"]) < 2:
            pytest.skip("Need at least 2 months for MoM")
        second = dashboard["months"][1]
        assert "mom" in second
