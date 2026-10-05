"""Shared helpers for day-report and submission dashboards."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Optional


def day_report_bounds_and_defaults(dates: List[str]) -> Dict[str, Dict[str, str]]:
    if not dates:
        return {"bounds": {}, "defaultRange": {}}
    min_date = min(dates)
    max_date = max(dates)
    max_dt = date.fromisoformat(max_date)
    min_dt = date.fromisoformat(min_date)
    default_start = max(min_dt, max_dt - timedelta(days=30))
    return {
        "bounds": {"start": min_date, "end": max_date},
        "defaultRange": {"start": default_start.isoformat(), "end": max_date},
    }


def submission_summary(months: List[dict]) -> Dict[str, int]:
    total = sum(row.get("submissions", 0) for row in months)
    average = round(total / len(months)) if months else 0
    return {"total": total, "average": average}
