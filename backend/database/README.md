# MarketingMind AI — Database

PostgreSQL schema for MarketingMind AI (**31 tables**).

## Files

| File | Description |
|------|-------------|
| [`schema.sql`](schema.sql) | Complete DDL — DROP, CREATE TABLE, indexes, comments |
| [`SCHEMA.md`](SCHEMA.md) | Table inventory, connection notes, notification tables |

## Quick start

```powershell
# Schema only (no seed)
psql -U postgres -h localhost -d postgres -f database/schema.sql

# Schema + demo seed data
cd backend
python scripts/init_postgres_schema.py
```

## Regenerate SQL from models

```powershell
cd backend
python scripts/generate_schema_sql.py
```

## Connection

Set in `backend/.env`:

```env
DATABASE_URL=postgresql+psycopg://postgres:admin@localhost:5432/postgres
USE_SEED_DATA=false
```

## Table groups

| Group | Count | Tables |
|-------|-------|--------|
| Auth & users | 3 | users, user_settings, auth_sessions |
| Campaigns | 5 | campaign_settings, contact_lists, campaign_contacts, campaign_templates, campaign_items |
| Job automation | 11 | job_profiles, job_automation_settings, search_configs, portals, carriers, job_results, saved_jobs, job_applications, tailored_resumes, linkedin_jobs, job_analyses |
| LinkedIn recruiter | 8 | linkedin_recruiters, linkedin_sequences, linkedin_sequence_steps, linkedin_followups, linkedin_message_templates, linkedin_settings, linkedin_api_sources, linkedin_api_keys |
| Reporting | 2 | day_report_rows, submission_months |
| Notifications | 1 | notification_deliveries |

`user_settings` includes email and SMS notification preference columns.
