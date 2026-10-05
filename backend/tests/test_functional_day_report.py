"""Functional API tests — Day report (DR-* / FUNCTIONAL_TEST_CASES.md)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.day_report


class TestDayReportDashboard:
    def test_dashboard_load(self, client, user_headers):
        response = client.get("/api/day-report/dashboard", headers=user_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["totals"]["linkedin"] >= 0
        assert body["totals"]["calls"] >= 0
        assert isinstance(body["rows"], list)
        assert isinstance(body["recruiters"], list)

    def test_filter_all_recruiters(self, client, user_headers):
        dashboard = client.get("/api/day-report/dashboard", headers=user_headers).json()
        start = dashboard["range"]["start"]
        end = dashboard["range"]["end"]
        response = client.post(
            "/api/day-report/filter",
            headers=user_headers,
            json={"start": start, "end": end, "recruiter": None},
        )
        assert response.status_code == 200
        filtered = response.json()
        assert filtered["totals"]["calls"] >= 0
        assert len(filtered["rows"]) >= 0

    def test_filter_by_recruiter(self, client, user_headers):
        dashboard = client.get("/api/day-report/dashboard", headers=user_headers).json()
        recruiters = dashboard.get("recruiters") or []
        if not recruiters:
            pytest.skip("No recruiters in day report seed data")
        recruiter = recruiters[0]
        response = client.post(
            "/api/day-report/filter",
            headers=user_headers,
            json={
                "start": dashboard["range"]["start"],
                "end": dashboard["range"]["end"],
                "recruiter": recruiter,
            },
        )
        assert response.status_code == 200
        rows = response.json()["rows"]
        assert all(row["recruiter"] == recruiter for row in rows)

    def test_filter_narrow_range(self, client, user_headers):
        response = client.post(
            "/api/day-report/filter",
            headers=user_headers,
            json={"start": "2099-01-01", "end": "2099-01-02", "recruiter": None},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["totals"]["linkedin"] == 0
        assert body["totals"]["calls"] == 0
        assert body["rows"] == []

    def test_filter_supports_open_ended_ranges(self, client, user_headers):
        dashboard = client.get("/api/day-report/dashboard", headers=user_headers).json()
        end = dashboard.get("bounds", {}).get("end") or dashboard["range"]["end"]
        response = client.post(
            "/api/day-report/filter",
            headers=user_headers,
            json={"start": None, "end": end, "recruiter": None},
        )
        assert response.status_code == 200
        assert all(row["date"] <= end for row in response.json()["rows"])
