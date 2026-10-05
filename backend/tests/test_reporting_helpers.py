"""Unit tests for reporting helpers (DR-* / SP-* calculations)."""

from __future__ import annotations

import pytest

from app.services.reporting_helpers import day_report_bounds_and_defaults, submission_summary

pytestmark = pytest.mark.reporting


class TestSubmissionSummary:
    def test_sp_summary_full_range(self):
        months = [
            {"month": "2025-11", "submissions": 24},
            {"month": "2025-12", "submissions": 28},
            {"month": "2026-01", "submissions": 31},
            {"month": "2026-02", "submissions": 34},
            {"month": "2026-03", "submissions": 39},
            {"month": "2026-04", "submissions": 42},
            {"month": "2026-05", "submissions": 47},
        ]
        result = submission_summary(months)
        assert result["total"] == 245
        assert result["average"] == 35

    def test_sp_summary_single_month(self):
        result = submission_summary([{"month": "2026-03", "submissions": 39}])
        assert result == {"total": 39, "average": 39}

    def test_sp_summary_empty(self):
        assert submission_summary([]) == {"total": 0, "average": 0}


class TestDayReportBounds:
    def test_dr_default_range_last_30_days(self):
        dates = ["2026-01-01", "2026-02-15", "2026-03-01"]
        result = day_report_bounds_and_defaults(dates)
        assert result["bounds"]["start"] == "2026-01-01"
        assert result["bounds"]["end"] == "2026-03-01"
        assert result["defaultRange"]["end"] == "2026-03-01"
        assert result["defaultRange"]["start"] == "2026-01-30"

    def test_dr_empty_dates(self):
        assert day_report_bounds_and_defaults([]) == {"bounds": {}, "defaultRange": {}}
