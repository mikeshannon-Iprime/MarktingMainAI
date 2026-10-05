#!/usr/bin/env python3
"""Generate backend/database/schema.sql from SQLAlchemy models."""
from __future__ import annotations

import re
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from app.db.models import Base

import app.db.models  # noqa: F401 — register all models

OUTPUT = BACKEND_ROOT / "database" / "schema.sql"

TABLE_GROUPS: list[tuple[str, list[str]]] = [
    (
        "Auth & users",
        ["users", "user_settings", "auth_sessions"],
    ),
    (
        "Campaigns",
        [
            "campaign_settings",
            "contact_lists",
            "campaign_contacts",
            "campaign_templates",
            "campaign_items",
        ],
    ),
    (
        "Job automation",
        [
            "job_profiles",
            "job_automation_settings",
            "search_configs",
            "portals",
            "carriers",
            "job_results",
            "saved_jobs",
            "job_applications",
            "tailored_resumes",
            "linkedin_jobs",
            "job_analyses",
        ],
    ),
    (
        "LinkedIn recruiter",
        [
            "linkedin_recruiters",
            "linkedin_sequences",
            "linkedin_sequence_steps",
            "linkedin_followups",
            "linkedin_message_templates",
            "linkedin_outreach_queue",
            "linkedin_settings",
            "linkedin_api_sources",
            "linkedin_api_keys",
        ],
    ),
    (
        "Reporting",
        ["day_report_rows", "submission_months", "notification_deliveries"],
    ),
]

TABLE_COMMENTS: dict[str, str] = {
    "users": "Application accounts (recruiter, admin, super_admin)",
    "user_settings": "Per-user notification and UI preferences",
    "auth_sessions": "Bearer token sessions",
    "campaign_settings": "SMTP and campaign delivery options per user",
    "contact_lists": "Named email recipient lists",
    "campaign_contacts": "Individual campaign recipients",
    "campaign_templates": "Reusable email templates",
    "campaign_items": "Campaign runs (draft, scheduled, sent)",
    "job_profiles": "Candidate profile, resume metadata, skills (JSONB)",
    "job_automation_settings": "Auto-apply threshold, schedule, toggles",
    "search_configs": "Job search titles, skills, filters (JSONB arrays)",
    "portals": "Job board URLs per user (Dice, Monster, etc.)",
    "carriers": "Company career page monitors",
    "job_results": "Scraped/matched job listings (manual integer PK)",
    "saved_jobs": "User favorites junction (user_id, job_result_id)",
    "job_applications": "Application tracker pipeline rows",
    "tailored_resumes": "Per-job tailored CV content",
    "linkedin_jobs": "LinkedIn job search cache",
    "job_analyses": "CV vs job fit analysis results",
    "linkedin_recruiters": "Discovered recruiter profiles",
    "linkedin_sequences": "Multi-step outreach sequences",
    "linkedin_sequence_steps": "Steps within an outreach sequence",
    "linkedin_followups": "Due follow-up reminders",
    "linkedin_message_templates": "Outreach message templates",
    "linkedin_outreach_queue": "Scheduled LinkedIn outreach delivery queue",
    "linkedin_settings": "LinkedIn automation limits and flags",
    "linkedin_api_sources": "Third-party enrichment providers catalog",
    "linkedin_api_keys": "API keys per user and provider",
    "day_report_rows": "Daily recruiter KPI activity rows",
    "submission_months": "Monthly submission totals for MoM/YoY charts",
    "notification_deliveries": "Audit log for email and SMS notification deliveries",
}


def _format_create_table(ddl: str) -> str:
    """Normalize CREATE TABLE formatting for readability."""
    ddl = ddl.strip()
    if ddl.endswith(")"):
        ddl = ddl + ";"
    ddl = re.sub(r"\)\s*;\s*;", ");", ddl)
    ddl = re.sub(r",\s+", ",\n\t", ddl)
    ddl = ddl.replace("(\n\t", "(\n\t", 1)
    return ddl


def main() -> None:
    dialect = postgresql.dialect()
    table_by_name = Base.metadata.tables
    ordered_names = [name for _, names in TABLE_GROUPS for name in names]
  # include any table not listed in groups (safety)
    for name in Base.metadata.sorted_tables:
        if name.name not in ordered_names:
            ordered_names.append(name.name)

    table_count = len(Base.metadata.tables)
    lines: list[str] = [
        "-- =============================================================================",
        "-- MarketingMind AI — PostgreSQL Database Schema",
        "-- =============================================================================",
        f"-- Source:     app/db/models.py (SQLAlchemy 2.x)",
        f"-- Tables:     {table_count}",
        "-- PostgreSQL: 14+",
        "-- Generator:  scripts/generate_schema_sql.py",
        "--",
        "-- Apply schema only (no seed data):",
        "--   psql -U postgres -d postgres -f database/schema.sql",
        "--",
        "-- Apply schema + seed demo data:",
        "--   python scripts/init_postgres_schema.py",
        "-- =============================================================================",
        "",
        "BEGIN;",
        "",
        "-- -----------------------------------------------------------------------------",
        "-- Drop existing tables (reverse dependency order)",
        "-- -----------------------------------------------------------------------------",
    ]

    for table in reversed(Base.metadata.sorted_tables):
        lines.append(f"DROP TABLE IF EXISTS {table.name} CASCADE;")

    for group_name, table_names in TABLE_GROUPS:
        lines.extend(
            [
                "",
                "-- -----------------------------------------------------------------------------",
                f"-- {group_name}",
                "-- -----------------------------------------------------------------------------",
            ]
        )
        for table_name in table_names:
            table = table_by_name[table_name]
            comment = TABLE_COMMENTS.get(table_name, "")
            lines.append(f"\n-- Table: {table_name}" + (f" — {comment}" if comment else ""))
            ddl = str(CreateTable(table).compile(dialect=dialect))
            lines.append(_format_create_table(ddl))

    lines.extend(
        [
            "",
            "-- -----------------------------------------------------------------------------",
            "-- Indexes",
            "-- -----------------------------------------------------------------------------",
        ]
    )

    for table_name in ordered_names:
        table = table_by_name[table_name]
        for idx in sorted(table.indexes, key=lambda i: i.name or ""):
            ddl = str(CreateIndex(idx).compile(dialect=dialect)) + ";"
            lines.append(ddl)

    lines.extend(
        [
            "",
            "-- -----------------------------------------------------------------------------",
            "-- Table comments",
            "-- -----------------------------------------------------------------------------",
        ]
    )
    for table_name in ordered_names:
        comment = TABLE_COMMENTS.get(table_name)
        if comment:
            safe = comment.replace("'", "''")
            lines.append(f"COMMENT ON TABLE {table_name} IS '{safe}';")

    lines.extend(["", "COMMIT;", ""])

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUTPUT} ({len(lines)} lines, {len(Base.metadata.tables)} tables)")


if __name__ == "__main__":
    main()
