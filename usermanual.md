# MarketingMind AI — End-to-End User Manual

**Document version:** 3.2
**Last updated:** 2026-09-05

---

## Table of Contents

1. [Overview](#1-overview)
2. [Who This Manual Is For](#2-who-this-manual-is-for)
3. [Tech Stack](#3-tech-stack)
4. [Project Structure](#4-project-structure)
5. [Prerequisites](#5-prerequisites)
6. [Complete Local Setup Guide](#6-complete-local-setup-guide)
7. [Run Frontend and Backend](#7-run-frontend-and-backend)
8. [Frontend Navigation](#8-frontend-navigation)
9. [Authentication and RBAC](#9-authentication-and-rbac)
10. [Module Usage](#10-module-usage)
11. [Backend API Reference](#11-backend-api-reference)
12. [Swagger API Usage](#12-swagger-api-usage)
13. [Test Data Operations](#13-test-data-operations)
14. [PostgreSQL Database Schema](#14-postgresql-database-schema)
15. [Configuration Reference](#15-configuration-reference)
16. [Build and Validation](#16-build-and-validation)
17. [Troubleshooting](#17-troubleshooting)
18. [Known Limitations](#18-known-limitations)
19. [Operational Recommendations](#19-operational-recommendations)
20. [Quick Start Checklist](#20-quick-start-checklist)
21. [Automated Testing & QA](#21-automated-testing--qa)
22. [Production Logging](#22-production-logging)
23. [Notifications, Email & SMS](#23-notifications-email--sms)
24. [Related Documentation](#24-related-documentation)

---

## 1. Overview

MarketingMind AI is a full-stack recruiter operations workspace for IT staffing teams. It unifies campaign email operations, job search automation, LinkedIn recruiter outreach, daily activity reporting, and submission analytics in one React console backed by a FastAPI API.

**What you can do:**

- Run mass email campaigns to vendor and buyer contacts
- Automate job search, fit analysis, and application tracking for consultants
- Discover LinkedIn recruiters, enrich profiles, and generate outreach messages
- Review recruiter day reports and month-over-month submission trends
- Explore the live API catalog and test endpoints in Swagger
- Manage your user profile, settings, and notifications

**How data works today:**

- **PostgreSQL** is the primary persistence layer when `DATABASE_URL` is set (`USE_SEED_DATA=false` by default)
- API routes delegate to `pg_store` for campaigns, job automation, LinkedIn recruiter, reporting, and auth
- **Per-user data scoping** — each authenticated user sees and updates their own job profile, automation settings, portals, and applications
- **JSON seed data** (`backend/app/data/test_data.json`) is used only when `USE_SEED_DATA=true` or PostgreSQL is not configured
- SQL tables are auto-created on backend startup when `DATABASE_URL` is set; run `init_postgres_schema.py` once to seed demo rows
- Auth uses PostgreSQL-backed sessions when the database is available (demo accounts seeded on startup). Session tokens are stored in the browser (localStorage) so a login survives page reloads, and the backend uses **sliding expiry** — active users automatically get their session renewed, so they stay logged in while they keep using the app
- Each user can upload and hold **multiple CVs / profiles**; every upload is parsed with AI and stored in the per-user CV library (`user_resumes`) with an **isolated profile snapshot** (contact, work prefs, skills, titles, summary). Exactly one CV is **Active** for matching, Quick Apply, and the My Profile form at a time. Switching Active reloads that CV’s snapshot without merging data from other CVs.

This guide covers setup, daily usage, roles and permissions, API reference, and troubleshooting.

---

## 2. Who This Manual Is For

| Audience | Use this manual to… |
|----------|---------------------|
| **Recruiters / bench sales** | Run campaigns, search jobs, track submissions, use LinkedIn outreach |
| **Team leads** | Review day reports, monitor submission trends, check operational metrics |
| **Admins** | Configure SMTP, API keys, launch campaigns, manage job automation |
| **Developers** | Set up locally, use API Explorer/Swagger, extend seed data |
| **Super admins** | Reset or append test datasets for demos and QA |

---

## 3. Tech Stack

### Frontend (`frontend/`)

| Layer | Technology |
|-------|------------|
| Framework | React 19 |
| Build tool | Vite 8 |
| Routing | React Router DOM 7 |
| HTTP client | Axios |
| Charts | Recharts |
| Icons | Lucide React |
| Excel import | xlsx (job portal/carrier batch upload) |

### Backend (`backend/`)

| Layer | Technology |
|-------|------------|
| API | FastAPI 0.116 |
| Server | Uvicorn |
| Validation | Pydantic / pydantic-settings |
| SQL ORM | SQLAlchemy 2 + PostgreSQL (psycopg 3) |
| Resume AI | LangChain, langchain-openai, scikit-learn, pypdf, python-docx |
| DB driver | `psycopg[binary]` |

---

## 4. Project Structure

```
MarktingMindAI/
├── frontend/              # React + Vite web app
│   └── src/
│       ├── App.jsx        # Auth gate, routing, workspace loader
│       ├── api/client.js  # All API calls
│       ├── components/    # AppShell, AuthPanel, ErrorBoundary
│       ├── pages/         # One page per module
│       └── utils/         # logger.js, validators, reporting helpers + tests
├── backend/               # FastAPI API service
│   ├── app/
│   │   ├── api/routes.py  # REST endpoints
│   │   ├── core/          # Config, auth, logging, middleware
│   │   ├── data/          # Seed datasets
│   │   ├── db/            # SQLAlchemy models (32 tables)
│   │   └── services/      # pg_store, notification_service, campaign_email, sms_client
│   ├── tests/             # pytest functional API suite (113 tests)
│   ├── app/services/portal_apply/  # Supervised Quick Apply (Playwright) for job boards
│   ├── database/          # schema.sql, SCHEMA.md
│   └── scripts/           # init_postgres_schema.py, generate_schema_sql.py
├── backupfolder/          # Legacy HTML prototypes + FUNCTIONAL_TEST_CASES.md
├── docs/                  # DOCUMENTATION_INDEX.md, TESTING_GUIDE.md
├── uml-artifacts/         # PlantUML architecture diagrams
├── usermanual.md          # This document
└── usermanual.mfd         # Documentation manifest (JSON)
```

**Key data files:**

| File | Purpose |
|------|---------|
| `backend/app/data/test_data.default.json` | Baseline immutable dataset |
| `backend/app/data/test_data.json` | Runtime mutable dataset (reset target) |

**Legacy HTML prototypes** (reference only, in `backupfolder/`): `job_automation_platform.html`, `campaigns_tab_mass_email.html`, `day_to_day_report_dashboard.html`, `linkedin_recruiter_discovery_panel.html`. Functional test cases: `backupfolder/FUNCTIONAL_TEST_CASES.md`.

---

## 5. Prerequisites

Install these **before** first-time setup. Confirm each command prints a version.

| Tool | Version | Check command |
|------|---------|---------------|
| Node.js | 18+ | `node -v` |
| npm | 9+ | `npm -v` |
| Python | 3.12 recommended (3.9+) | `python --version` |
| pip | Latest | `python -m pip --version` |
| PostgreSQL | 14+ | `psql --version` |

**Required for local data:**

- PostgreSQL running on `localhost:5432`
- Default connection used by this repo: user `postgres`, password `admin`, database `postgres`
- Create the database if it does not exist: `CREATE DATABASE postgres;` (or change `DATABASE_URL`)

**Optional (features work in fallback/demo mode without these):**

- Playwright Chromium (supervised Quick Apply)
- OpenAI API key or local Ollama (resume AI / LLM insights)
- Apify API token (live LinkedIn job scraping)
- SMTP / Twilio (live email and SMS)
- Third-party keys: Apollo, Hunter, RocketReach, Lusha, LinkedIn

**This machine’s usual local URLs (after setup):**

| Service | URL |
|---------|-----|
| Web app | http://localhost:5173 |
| API (this workspace) | http://127.0.0.1:8002 |
| Swagger | http://127.0.0.1:8002/docs |

Port **8000** is the documented default. This project commonly uses **8002** when 8000 is busy. Frontend `VITE_API_BASE_URL` **must** match the backend port.

---

## 6. Complete Local Setup Guide

Do these steps **once** on a new machine. After that, use [Section 7](#7-run-frontend-and-backend) to start the apps.

Open a terminal in the repo root:

`MarktingMindAI/` (folder that contains `frontend/` and `backend/`).

### 6.1 Clone or open the repo

```powershell
cd C:\Users\LENOVO\Downloads\MarktingMindAI\MarktingMindAI
```

macOS / Linux: `cd /path/to/MarktingMindAI`.

### 6.2 Backend — virtual env, packages, env file

**Windows (PowerShell):**

```powershell
cd backend
copy .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If `Activate.ps1` is blocked: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or skip activation and always call `.\.venv\Scripts\python.exe`.

**macOS / Linux:**

```bash
cd backend
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Edit `backend/.env` (minimum for local PostgreSQL):**

```env
DATABASE_URL=postgresql+psycopg://postgres:admin@localhost:5432/postgres
USE_SEED_DATA=false
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
JWT_SECRET=your-secret-key-change-in-production
```

Match `postgres` / `admin` / database name to your local PostgreSQL install.

### 6.3 PostgreSQL schema + demo users

Start PostgreSQL, then from `backend/` (venv active):

```powershell
python scripts/init_postgres_schema.py
```

This creates tables (32) and seeds demo accounts. On later backend starts, tables are also ensured via `create_all`.

**Demo logins (email = username):**

| Role | Email | Password |
|------|-------|----------|
| Super Admin | `superadmin@marketingmind.ai` | `Super@123` |
| Admin | `admin@marketingmind.ai` | `Admin@123` |
| User | `user@marketingmind.ai` | `User@123` |

### 6.4 Playwright browsers (Quick Apply)

From `backend/` (venv active):

```powershell
python -m playwright install chromium
```

Optional: keep browsers under the repo (used by this workspace):

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH='.playwright-browsers'
python -m playwright install chromium
```

Set the same path in `backend/.env`: `PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers`.

### 6.5 Frontend — packages and API URL

**Windows (PowerShell):**

```powershell
cd frontend
copy .env.example .env
npm install
```

**macOS / Linux:**

```bash
cd frontend
cp .env.example .env
npm install
```

**Edit `frontend/.env` so it matches the backend port you will use.**

If backend runs on **8000** (documented default):

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_LOG_LEVEL=debug
```

If backend runs on **8002** (this workspace’s usual port):

```env
VITE_API_BASE_URL=http://127.0.0.1:8002
VITE_LOG_LEVEL=debug
```

Restart Vite after changing `.env` (Vite only reads env at startup).

### 6.6 Environment variables (full reference)

Copy `backend/.env.example` → `backend/.env` and adjust as needed.

| Variable | Default / Example | Purpose |
|----------|-------------------|---------|
| `DATABASE_URL` | `postgresql+psycopg://postgres:admin@localhost:5432/postgres` | PostgreSQL connection |
| `USE_SEED_DATA` | `false` | When `true`, API reads/writes JSON test datasets instead of PostgreSQL |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_FROM_EMAIL` | (empty) | Live campaign email delivery via SMTP |
| `CAMPAIGN_FORCE_DEMO_MODE` | `false` | When `true`, campaign sends are simulated even if SMTP is configured |
| `NOTIFICATION_FROM_NAME` | `MarketingMind AI` | Sender display name for transactional notification emails |
| `NOTIFICATION_FROM_EMAIL` | (empty) | Override from-address for notifications; falls back to SMTP username |
| `NOTIFICATION_FORCE_DEMO_MODE` | `false` | When `true`, notification email/SMS are simulated |
| `SMS_PROVIDER` | `demo` | `demo` or `twilio` for SMS delivery |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_FROM_NUMBER` | (empty) | Twilio credentials for live SMS |
| `OPENAI_API_KEY` | (empty) | Optional OpenAI fallback when Ollama is unavailable |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `USE_LOCAL_LLM` | `true` | Prefer Ollama/Mistral for reasoning (skill extraction, gap analysis, ranking explanations) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API base URL |
| `OLLAMA_MODEL` | `mistral` | Local model for LLM reasoning layer |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Open-source embeddings for CV ↔ job similarity (primary scorer) |
| `EMBEDDING_BACKEND` | `sklearn_tfidf` | `auto`, `sentence_transformers`, or `sklearn_tfidf` (fastest local startup) |
| `RESUME_PARSE_INCLUDE_LLM` | `false` | Force LLM during resume parse; auto-enables when Ollama/OpenAI is reachable if `false` |
| `RESUME_PARSE_LLM_TIMEOUT_SECONDS` | `10` | Max seconds to wait for LLM during resume parse before rule/ML fallback |
| `OLLAMA_TIMEOUT_SECONDS` | `120` | Default timeout for Ollama chat calls (job ranking explanations) |
| `APIFY_API_TOKEN` | (empty) | Apify token for live LinkedIn job scraping; empty = simulated scrape fallback |
| `USE_APIFY_SCRAPER` | `true` | Use Apify for LinkedIn portals when token is set |
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://localhost:3000` | CORS origins (comma-separated in `.env.example`) |
| `JWT_SECRET` | (change in production) | Token signing secret |
| `LOG_LEVEL` | `INFO` | Backend log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `ENVIRONMENT` | `development` | Affects default log format (`production` uses JSON logs) |
| `APOLLO_API_KEY` | (empty) | Apollo.io enrichment |
| `HUNTER_API_KEY` | (empty) | Hunter.io email finder |
| `LINKEDIN_API_KEY` | (empty) | LinkedIn API access |

**Feature flags** in `.env.example`:

```env
ENABLE_CAMPAIGN_MODULE=true
ENABLE_JOB_AUTOMATION=true
ENABLE_LINKEDIN_RECRUITER=true
ENABLE_REPORTING=true
```

---

## 7. Run Frontend and Backend

After Section 6 is done, start **two terminals** every time you develop. Leave both running.

### 7.1 Start backend

**Windows — port 8002 (recommended if 8000 is busy):**

```powershell
cd backend
$env:PLAYWRIGHT_BROWSERS_PATH='.playwright-browsers'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8002
```

**Windows — port 8000 (documented default):**

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**macOS / Linux:**

```bash
cd backend
source .venv/bin/activate
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Wait until the log shows **Application startup complete** and `Uvicorn running on http://127.0.0.1:<port>`.

On startup the API creates missing SQL tables, verifies auth seed, and warms embeddings. First start can take longer while sentence-transformers/sklearn loads.

**Confirm API:** open http://127.0.0.1:8002/docs (or `:8000/docs`). Swagger UI should load without logging in. Authenticated routes still need a Bearer token.

### 7.2 Start frontend

Second terminal:

```powershell
cd frontend
npm run dev -- --port 5173 --strictPort
```

Wait for:

```text
➜  Local:   http://localhost:5173/
```

`--strictPort` stops Vite from silently moving to 5174+.

### 7.3 Access URLs

| Resource | Default (8000) | This workspace (8002) |
|----------|----------------|------------------------|
| Web app | http://localhost:5173 | http://localhost:5173 |
| Swagger | http://127.0.0.1:8000/docs | http://127.0.0.1:8002/docs |
| ReDoc | http://127.0.0.1:8000/redoc | http://127.0.0.1:8002/redoc |
| OpenAPI | http://127.0.0.1:8000/openapi.json | http://127.0.0.1:8002/openapi.json |

> **Note:** `GET /health` requires a valid bearer token (any logged-in role). Use Swagger **Authorize** after `POST /api/auth/login`.

**Health response fields:**

| Field | Description |
|-------|-------------|
| `status` | Overall API status (`ok` or `error`) |
| `database` | PostgreSQL connection status and message |
| `modules` | List of active module identifiers |

### 7.4 First login

1. Open http://localhost:5173
2. Sign in with a demo account from Section 6.3 (or use a Demo User card if shown)
3. Command Center should load module cards

If the UI shows a network/API error: backend is down, or `VITE_API_BASE_URL` does not match the backend port (restart Vite after fixing `.env`).

### 7.5 Stop or restart

**Stop:** in each terminal press `Ctrl+C`.

**Windows — free ports if a process is stuck:**

```powershell
foreach ($port in @(5173, 8002)) {
  Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}
```

Use `8000` instead of `8002` if that is the API port. Then start backend and frontend again (7.1 and 7.2).

**Flush demo data (optional, super admin):** `POST /api/meta/test-data/reset` drops and re-seeds PostgreSQL. This deletes local job results, applications, and sessions.

### 7.6 Port conflict

If 8000 is in use, run backend on **8002** and set:

```env
VITE_API_BASE_URL=http://127.0.0.1:8002
```

in `frontend/.env`, then restart Vite.

---

## 8. Frontend Navigation

Use the **left sidebar** to move between modules.

- Click **Refresh data** to flush the cached workspace and reload fresh data (overview, campaigns, job automation, day report, submissions, health). Local UI state (filters, selections, toasts) is cleared with the refresh.
- **LinkedIn Recruiter** loads its workspace independently when you open that page.
- Your name and role appear at the bottom of the sidebar; click to open **My Profile**.
- The **API status** badge shows backend health (`ok`, `error`, etc.).

| # | Route | Module | Purpose |
|---|-------|--------|---------|
| 1 | `/` | Command Center | Overview metrics, module cards, activity feed |
| 2 | `/campaigns` | Campaign Studio | Email campaigns and contact lists |
| 3 | `/job-automation` | Job Automation | Profile, search, portals, CV analyzer, tracker |
| 4 | `/linkedin` | LinkedIn Recruiter | Discovery, enrichment, outreach, sequences |
| 5 | `/day-report` | Day Report | Recruiter daily KPI charts |
| 6 | `/submissions` | Submissions | MoM/YoY submission trends |
| 7 | `/api-explorer` | API Explorer | Live endpoint catalog + Swagger links |
| 8 | `/profile` | My Profile | Profile, settings, notifications, password |

---

## 9. Authentication and RBAC

Login is required for all API-backed screens. The auth panel appears when you are not signed in.

### 9.1 Demo Accounts

| Role | Email | Password |
|------|-------|----------|
| Super Admin | `superadmin@marketingmind.ai` | `Super@123` |
| Admin | `admin@marketingmind.ai` | `Admin@123` |
| User (recruiter) | `user@marketingmind.ai` | `User@123` |

On the login screen, click any **Demo Users** card to auto-fill credentials.

### 9.2 Login / Register / Logout

1. Open http://localhost:5173
2. **Login** with a demo account, or switch to **Register** to create a new account
3. Registration requires name, email, password (6+ chars), and role selection
4. The app stores a bearer token in `localStorage` and loads workspace data
5. Click **Logout** in the sidebar to end the session

> **Demo security note:** Registration allows selecting any role including `super_admin`. This is intentional for local demos only — restrict registration in production.

### 9.3 Role Permissions

| Capability | user | admin | super_admin |
|------------|:----:|:-----:|:-----------:|
| View dashboards and workspaces | Yes | Yes | Yes |
| My Profile (settings, password, notifications) | Yes | Yes | Yes |
| Campaign preview, job analyze, save job | Yes | Yes | Yes |
| LinkedIn discover, enrich, generate message | Yes | Yes | Yes |
| LinkedIn save (bookmark) recruiter, CSV import | Yes | Yes | Yes |
| Job profile save, automation settings, search config save | Yes | Yes | Yes |
| **Run auto apply now** | Yes | Yes | Yes |
| Resume parse, tailor, save tailored CV | Yes | Yes | Yes |
| **Job search run, Quick apply / batch apply** | Yes | Yes | Yes |
| Launch campaigns, test-send, campaign settings | No | Yes | Yes |
| Portal/carrier CRUD | No | Yes | Yes |
| LinkedIn outreach queue / scheduled outreach | No | Yes | Yes |
| LinkedIn save message template | No | Yes | Yes |
| LinkedIn API key / settings update | No | Yes | Yes |
| View test data dump (`/api/meta/test-data`) | No | Yes | Yes |
| Append test data | No | No | Yes |
| Reset test data to baseline | No | No | Yes |

The `user` role has full access to **My Profile** and **Job Automation** profile/automation/search-config/search-run/auto-apply/Quick-apply flows (scoped to their own account). Campaign launch, portal/carrier management, and LinkedIn outreach queue remain admin-only.

---

## 10. Module Usage

### 10.1 Command Center

**Route:** `/`

Use this page to:

- Review high-level metrics (campaign throughput, automation queue)
- Open workspace modules from the cards (campaigns, job automation, day report, submissions)
- Read the recent activity feed and workspace notes

The sidebar shows **API status** (`ok`, `error`, etc.) and a **Refresh data** control. Database health tiles are not shown on this page.

### 10.2 Campaign Studio

**Route:** `/campaigns`

**Tabs:** Compose · Contacts · Campaigns · Templates · Settings

#### Compose tab

1. Write email **subject** and **body**
2. Use the rich-text toolbar (bold, italic, underline, bullet/numbered lists, link, table, styled **divider**, font size/color) and **merge tags** for personalization
3. Pick an **AI prompt template** to pre-fill content
4. Select **contact lists** and recipients
5. Click **Preview** to render HTML — the preview renders from the backend, and if the backend is unreachable a **local client-side preview** (with merge tags substituted) is shown instead so you are never blocked
6. **Test send** (admin/super_admin) or open the **scheduler** to launch

The **Emails sent** hero metric animates (counts up) after an immediate send so the delivery increment is visible.

**Scheduler options:**

| Option | Description |
|--------|-------------|
| Send date / time | Schedule future delivery |
| Send now | Ignore schedule and send immediately |
| Open tracking | Track email opens |
| Auto follow-up | Queue a follow-up sequence |

#### Contacts tab

- Browse and filter campaign contacts
- View status (Queued, Sent, Opened, Bounced)
- Create new contact lists (admin/super_admin)

#### Campaigns tab

- View campaign history with status (Sent, Scheduled, Draft)
- Filter by status
- Track progress bars per campaign

#### Templates tab

- Browse saved email templates
- Preview template HTML
- Use templates as starting points for new campaigns

#### Settings tab

- **SMTP:** host, port, username, password, from address
- **Test SMTP** (`POST /api/campaigns/test-smtp`) — verify live connection (admin+)
- **Compliance:** unsubscribe footer, CAN-SPAM toggles
- **Warmup:** sender reputation settings

When SMTP is configured and `CAMPAIGN_FORCE_DEMO_MODE=false`, **Launch** and **Test send** deliver real email via `campaign_email.py` with merge tags and throttling.

**Merge tags:**

| Tag | Replaced with |
|-----|---------------|
| `{{candidate_name}}` | Consultant name |
| `{{recruiter_name}}` | Sender name |
| `{{company_name}}` | Your company |
| `{{skills}}` | Skill list |
| `{{location}}` | Location |
| `{{rate}}` | Bill rate |

**AI prompt templates:** Hotlist blast, Candidate intro, Follow-up, Urgent placement, Bench sales, Re-introduction

### 10.3 Job Automation

**Route:** `/job-automation`

The React Job Automation module matches (and extends) the legacy HTML prototype (`backupfolder/job_automation_platform.html`). A **● LIVE** badge, 4-metric hero row (applied today, new matches, interviews, avg match), bottom-right toast notifications, and tab count badges are shown in the UI.

**Tabs:** My Profile · Job Search · Portals · Results · CV Analyzer · LinkedIn · Tracker

> **Role note:** **Run Search** and portal/carrier CRUD require **admin** or **super_admin**. The `user` role can save profile, automation settings, search config, and run **auto apply** on their own scoped workspace.

#### 10.3.1 My Profile (multi-profile / multi-CV)

Job Automation → **My Profile** is the multi-profile workspace: each uploaded resume owns an **isolated profile** (contact + preferences + parsed skills). This is separate from account settings at `/profile` ([§10.8](#108-my-profile)).

| Feature | Description |
|---------|-------------|
| Personal fields | Name, email, phone, location, LinkedIn, expected rate — **scoped to the Active CV** |
| Experience | **Text field** for total experience (e.g. `5 years`, `8+ years`) |
| Dropdowns | Employment type (C2C, W2, Full Time, C2H, Both), visa, work mode |
| 4-stat row | Applied today, new matches, interviews, avg match score |
| Resume upload | Multi-select `.pdf`, `.docx`, `.txt` via file picker; staged files show in a queue and parse **one by one** |
| **Parse with AI** | Calls `POST /api/job-automation/resume/parse` per file; updates **only that CV’s isolated snapshot** plus the active `job_profiles` / search working copy (**replace**, not merge) |
| **CV library** | Multiple CVs in `user_resumes`, each with `profile_snapshot`. Exactly one is *Active*. **Set active** reloads that CV’s full snapshot into the form. Trash removes a CV; newest remaining becomes Active and hydrates the form |
| Parse results panel | Role-fit %, matched/missing skills, AI insights, text preview — for the Active CV only |
| Auto-apply panel | Match threshold slider (50–95%), max applications/day (blank = default 20 on save), schedule time/timezone, search schedule label |
| Automation toggles | Send alerts, **Tailor CV Automatically**, **Scheduled Discovery** |
| **Run auto apply now** | Scrapes portals, ranks matches, applies to top roles using the **Active** CV, navigates to **Results** |
| Save active profile | Persists the Active CV into `job_profiles` and syncs that CV’s `profile_snapshot` only |

##### Multi-profile model

```
user_resumes (many per user)
  ├─ CV A  profile_snapshot { name, email, prefs, skills, titles, summary }  is_active=false
  ├─ CV B  profile_snapshot { … }  is_active=true   ← form + apply/search use this
  └─ CV C  profile_snapshot { … }  is_active=false

job_profiles (one row per user)  = working copy of the Active CV
search_configs                   = titles/skills replaced from the Active CV snapshot
```

| Behavior | What happens |
|----------|----------------|
| Parse CV A then CV B | B becomes Active. A’s skills/contact stay on A’s snapshot; they are **not** merged into B |
| **Set active** on A | Form + `job_profiles` + search titles/skills reload from A’s snapshot |
| **Save active profile** while A is Active | Only A’s `profile_snapshot` is updated; B and C unchanged |
| Delete Active CV | Newest remaining CV becomes Active and hydrates the form |
| Re-upload same file name | Refreshes that CV’s parse/snapshot and makes it Active |

##### Parse with AI workflow

1. Upload one or more resume files (multi-select stages a queue)
2. Click **Parse with AI** — files are processed **sequentially** (progress: “Parsing 2 of 5…”)
3. Review extracted name, skills, job titles, and match score in the results panel
4. Each parse writes an isolated snapshot on that CV; the **last successful** parse becomes Active and **replaces** (does not merge) the working profile / search skills
5. Edit contact/prefs on the right → **Save active profile** (only the Active CV)
6. Use **Set active** anytime to switch profiles without re-uploading

##### UI layout (Job Automation → My Profile)

| Area | Contents |
|------|----------|
| Left | Multi-upload zone, parse queue, **Parse with AI** / Preview, Stored CVs library, Active CV parse panel |
| Right | Active profile form (contact + work prefs), Save active profile, Auto-apply settings |

> **Tip:** Keep one “Java” CV and one “Python” CV as separate profiles. Switch Active before search or Quick Apply so matching and applications use the correct skills and resume file bytes.

#### 10.3.2 Job Search

The **Job Search** tab includes the same **Auto-apply settings** panel as My Profile (Tailor CV, Scheduled Discovery, scheduled time/timezone, search schedule, and **Run auto apply now**).

| Feature | Description |
|---------|-------------|
| Job title tags | Add/remove titles with **Add** button or Enter — persists via `PUT /api/job-automation/search` |
| Required skills (AND) | Must-have skills tag editor |
| Optional skills (OR) | Nice-to-have skills tag editor |
| Add preset titles | Inserts Java, Python, Data Engineer, Full Stack Developer |
| Location & radius | Location text + radius preset dropdown (25/50/100 miles, Nationwide) |
| Job posted within | Last 24h through 30 days |
| Experience level | Any, Mid-Level, Senior, Lead/Principal |
| Rate range | Min/max hourly rate filters |
| Employment type | Full profile employment options |
| Match score | Slider for minimum match % |
| Repeat every | Once daily, every 6h, 3h, or 1h |
| Exclude keywords | Comma-separated exclusion list with an inline **Search** button — commits the keywords and immediately runs the portal search (also triggered by pressing **Enter** in the field) |
| **Save search config** | Persists all search fields to backend |
| **Run search now** | Saves config, scrapes portals, ranks matches with CV profile (embeddings primary; optional LLM explanations), shows progress bar, navigates to Results |
| **Run auto apply now** | Same as Profile tab — uses search titles or profile job titles as fallback; syncs results filter so matches appear on **Results** |

**Access:** Job search execution (**Run search now** / **Search**) and Quick Apply are available to the **user** role (scoped to their own account) as well as admin and super admin.

**Auto apply behavior:**

- Requires at least one **portal** and at least one **job title** (from Job Search tags or profile `jobTitles` from resume parse)
- Cleared **Max applications per day** stays blank in the UI; saves as **20** when you save profile/automation settings
- After run, the app always navigates to **Results** and adjusts the minimum match filter to include returned jobs

**Sales Automation job-board pipeline** (search and auto apply):

1. Scrape jobs from configured portals (live Dice public results by default; Apify LinkedIn when `APIFY_API_TOKEN` is set; resilient simulated fallback for unavailable providers)
2. Build CV text from saved profile (`job_profile` / parsed skills, summary, titles, experience)
3. Filter by search config (titles, skills, location, exclusions, posted date, min match)
4. **Primary match** — open-source embeddings (`all-MiniLM-L6-v2` or `sklearn_tfidf` fallback) compute cosine similarity between CV text and each job description; scores are **never** generated by the LLM
5. **Reasoning layer (optional)** — Ollama (`USE_LOCAL_LLM=true`, default) or OpenAI (`OPENAI_API_KEY`) explains fit for top ~15 results: role classification, ranking explanation, skill gaps
6. Rank and return results to the **Results** tab with `matchSource` (`embeddings`, `embeddings+llm`, or `ml` fallback) and `matchInsight` per card

Embeddings run locally without any API key. LLM is optional — if Ollama and OpenAI are both unavailable, embedding scores still rank results. See [§10.3.9](#1039-llm-in-job-automation--end-to-end) for full technical detail.

#### 10.3.3 Portals

| Feature | Description |
|---------|-------------|
| Portal list | Avatar initials, name, URL, Active/Paused toggle |
| Excel/CSV/XLSX upload | True `.xlsx` parsing via `xlsx` library; preview then **Confirm import** |
| Add portal | Manual name + URL entry |
| Delete portal | Remove with trash icon |
| Carrier pages | Career site URLs with **Monitoring** status badge |
| Carrier import | Batch upload via Excel/CSV/XLSX |

#### 10.3.4 Results

| Feature | Description |
|---------|-------------|
| Pipeline banner | Shows scrape → embeddings → LLM reasoning steps; embeddings-only vs embeddings+AI |
| Job cards | Checkbox selection, match %, match source (Embeddings / Embeddings+AI), match insight, skill gaps, skills, hot badge, portal name, rate, **apply status badge** (`Applying` → `Applied`) |
| AI / resume keyword textarea | Automatically populated from parsed CV matches, required/optional search skills, resume skills, and returned job skills; comma-separated; results match any keyword |
| Filters | Job type, sort, min match slider, exclude keywords with inline **Search** button (re-runs portal search using the current excludes). Posted-date filtering is configured on **Job Search**, not duplicated on Results. |
| Empty states | "No search results yet" prompt (with a **Go to Job Search** shortcut) before the first search, and a "No roles match the current filters" card (with **Clear Results filters**) when results exist but are filtered out |
| Results badge | The Results nav tab badge shows the total number of results (not the filtered count) |
| Bulk apply | Select all filtered → **Apply selected** (tracks applications; status appears on each card) |
| Per-card actions | **Quick apply** — supervised portal apply (profile + CV fill, optional auto-submit) for Dice, CareerBuilder, Monster, Indeed, ZipRecruiter, and LinkedIn; button flips to **Applied** when complete; Analyze; Save to favorites |
| Progress bar | Visual match score on each card |

**Quick Apply behavior (v3.0 — true portal apply):**

1. Collects the active profile + CV bytes from the resume library.
2. Starts a **supervised** browser session (Playwright Chromium) for supported job boards: **Dice**, **CareerBuilder**, **Monster**, **Indeed**, **ZipRecruiter**, **LinkedIn**.
3. Opens the posting URL, pauses for login/CAPTCHA if needed, clicks Apply, fills known fields, uploads the CV, and auto-submits when `PORTAL_APPLY_AUTO_SUBMIT=true`.
4. Polls application status until confirmation → tracker and **Results** card show **Applied**.
5. Unsupported / company career pages fall back to opening the URL for manual completion.
6. Modes: `PORTAL_APPLY_MODE=supervised` (live browser), `manual` (open URL + track), `demo` (mark Applied without a browser — used in automated tests).

"View on CareerBuilder" / "View on Monster" links still open the public posting; **Quick apply** runs the same automation path for every supported portal, not Dice alone.

#### 10.3.5 CV Analyzer

| Feature | Description |
|---------|-------------|
| Job reference | Optional dropdown from saved search results |
| Job description | Paste full JD text (20+ chars) for manual analysis |
| Analyze CV match | Runs `POST /api/job-automation/analyze` (keyword/heuristic overlap — **not** LLM-backed) |
| Empty state | Placeholder until first analyze in session |
| Summary tiles | Matched vs missing keyword counts |
| Conic score circle | Visual match % display |
| Recommendations | Per-suggestion **Apply** + **Apply all suggestions** |
| Tailor resume | `POST /api/job-automation/resume/tailor` — available after every successful analysis (no longer gated on the "Tailor CV Automatically" automation toggle; template assembly from analyze output — **not** LLM-backed) |
| Preview / save / download | Preview tailored CV, save to backend, download as `.txt` |

> **Note:** The **Tailor CV Automatically** toggle on My Profile / Job Search now controls only automated batch tailoring during auto-apply. The manual **Tailor resume** button in the analyzer is always available once an analysis has run.

#### 10.3.6 LinkedIn (within Job Automation)

| Feature | Description |
|---------|-------------|
| LinkedIn header | Blue panel with **Connected** badge |
| Filters | Query, company, experience level, employment type, date posted |
| Toggles | Under 10 applicants, Easy Apply only |
| Sort | Relevance, Most Recent, Most Applicants |
| Job cards | Company initials avatar, match %, mini match progress bar |
| Actions | Easy Apply / Apply on LinkedIn, open posting, save |

#### 10.3.7 Tracker

| Feature | Description |
|---------|-------------|
| Summary stats | Total applied, under review, interviews, action needed |
| Sub-tabs | All · Interviews · Action Needed · Stats |
| Interview / Action tabs | Summary cards (count, response rate, avg response time) |
| Application cards | Portal source, application date, match %, status (including Rejected) |
| Actions | **Follow up** (schedules reminder), **View posting** (opens URL when available) |
| Stats tab | Response rate, avg match, avg response time, best platform |

#### 10.3.8 Feature parity summary (HTML vs React)

| Area | React status |
|------|--------------|
| Profile fields + dropdowns | Yes |
| Resume upload + **Parse with AI** (backend) | Yes |
| Auto-apply + threshold slider | Yes |
| Job title / skill tag editors with **Add** + API persist | Yes |
| Search filters (posted within, experience, rate, repeat) | Yes |
| Portal XLSX import + preview | Yes |
| Results checkboxes + bulk apply | Yes |
| CV analyzer (conic score, apply all, tailor/save) | Yes |
| LinkedIn search/apply + sort + match bar | Yes |
| Tracker extended stats + portal/date on cards | Yes |
| LIVE badge + toast notifications + tab badges | Yes |

#### 10.3.9 LLM in Job Automation — End-to-End

This section documents how **LLM**, **embeddings**, and **ML heuristics** work together in Job Automation. The design is **embeddings-first, LLM-second**: match **scores** always come from embeddings (or ML fallback). The LLM adds explanations and resume insights when Ollama or OpenAI is available — it never replaces numeric ranking.

**Key backend modules:**

| Module | Path | Role |
|--------|------|------|
| Unified LLM client | `backend/app/services/llm_client.py` | Ollama first, OpenAI fallback, graceful skip |
| Embeddings | `backend/app/services/embedding_service.py` | Primary CV ↔ job similarity scorer |
| Job matching | `backend/app/services/job_match_ai.py` | Embed, rank, optional LLM explanations |
| Resume parse | `backend/app/services/resume_ai.py` | Rule + ML parse, optional LLM enrichment |
| Portal scrape | `backend/app/services/portal_scraper.py` | Apify LinkedIn or simulated jobs (no LLM) |

**Architecture overview:**

```
Frontend (JobAutomationPage.jsx)
    │
    ├─ Parse with AI ──► POST /resume/parse ──► resume_ai.py ──► llm_client.py (optional)
    │
    ├─ Run Search / Auto Apply ──► POST /search/run | /auto-apply
    │       └─► portal_scraper → filter → job_match_ai (embeddings + optional LLM)
    │
    └─ CV Analyzer / Tailor ──► POST /analyze | /resume/tailor (keyword heuristics only — no LLM)

llm_client.py ──► Ollama (mistral)  OR  OpenAI (gpt-4o-mini)
```

##### Unified LLM client (`llm_client.py`)

All LLM calls use `invoke_llm(system_prompt, user_prompt)`:

| Step | Behavior |
|------|----------|
| 1 | If `USE_LOCAL_LLM=true` → call **Ollama** at `OLLAMA_BASE_URL` (`/api/chat`, model `OLLAMA_MODEL`) |
| 2 | On timeout or error → fall back to **OpenAI** if `OPENAI_API_KEY` is set |
| 3 | If neither works → return empty content with `status: skipped` — **the pipeline does not fail** |

`llm_available()` probes Ollama (`/api/tags`) or checks for an OpenAI key. Job ranking uses `skip_if_unavailable=True` so missing LLM never blocks search or auto apply.

##### Path A — Resume parse (My Profile tab — multi-profile)

**Trigger:** Upload one or more resumes → **Parse with AI** (sequential per file)  
**API:** `POST /api/job-automation/resume/parse` → `parse_resume_with_ai()` → `apply_parsed_resume()` (isolated `profile_snapshot`)

| Stage | Service function | Uses LLM? |
|-------|------------------|-----------|
| Extract text from PDF/DOCX/TXT | `_extract_text()` | No |
| Structured profile (name, email, skills, titles) | `_rule_based_profile_parse()` | No |
| Role-fit score vs target role | `_ml_skill_assessment()` (keywords + TF-IDF cosine) | No |
| Insights, strengths, gaps, role classification | `_langchain_agent_assessment()` → `invoke_llm()` | **Optional** |
| Persist isolated CV + Active working copy | `pg_store.apply_parsed_resume()` | No |

LLM runs when `RESUME_PARSE_INCLUDE_LLM=true` **or** `llm_available()` returns true (Ollama up or OpenAI key set). The call is wrapped in `asyncio.wait_for` with budget `RESUME_PARSE_LLM_TIMEOUT_SECONDS + 2`. On timeout, parse still succeeds with rule-based + ML output; the UI shows the timeout in `llmAssessment.insights`.

**LLM prompt output (JSON):** `insights`, `strengths`, `improvements`, `extractedSkills`, `roleClassification`.

**Response fields:** `parsedProfile`, `mlAssessment`, `llmAssessment`, `agentTrace`, plus updated `profile`, `search`, and `resumes` (full CV library with per-CV `profileSnapshot` / `profileName` / `experience`) when persistence succeeds.

**Isolation:** Each parse writes only that file’s snapshot. Skills/titles from other CVs are **not** merged. The newly parsed CV becomes Active and **replaces** `job_profiles` / search titles & skills.

**Frontend:** `JobAutomationPage.jsx` queues multi-file uploads, parses sequentially, and binds the form to the Active CV only.

##### Path B — Search and Auto Apply (primary matching flow)

**Triggers:**

- **Run search now** → `POST /api/job-automation/search/run`
- **Run auto apply now** → `POST /api/job-automation/auto-apply`

Both invoke `enrich_and_rank_jobs()` in `job_match_ai.py` (via `pg_store._rank_jobs_with_cv` or seed-data equivalent).

**Pipeline steps:**

| Step | ID | Description | LLM? |
|------|-----|-------------|------|
| 1 | `scrape_portals` | Apify LinkedIn (`APIFY_API_TOKEN`) or simulated jobs per portal URL | No |
| 2 | `parse_cv_profile` | Build CV text from saved profile (`profile_to_cv_text()`) | No |
| 3 | `filter_jobs` | Titles, required/optional skills, location, posted date, rate, exclusions | No |
| 4 | `embedding_similarity` | Cosine similarity: CV text vs each job description; blend 80% embedding + 20% portal score when present; sort descending | No |
| 5 | `llm_reasoning` | Top ~15 jobs sent to LLM for explanations only (`_llm_explain_jobs()`) | **Optional** |
| 6 | `rank_results` | Apply `minMatchScore` / match threshold; fallback shows top N if none meet threshold | No |

**Embedding backends** (`EMBEDDING_BACKEND`):

| Value | Behavior |
|-------|----------|
| `auto` | Try `sentence-transformers/all-MiniLM-L6-v2`, fall back to sklearn TF-IDF |
| `sentence_transformers` | MiniLM only |
| `sklearn_tfidf` | Fast local dev fallback (no Hugging Face download) |

**LLM reasoning prompt** instructs the model: *"Do NOT replace embedding scores — only explain fit."* Returns JSON array per job: `jobId`, `roleClassification`, `rankingExplanation`, `skillGaps`.

When LLM succeeds, each job gets `matchSource: embeddings+llm` and enriched `matchInsight`, `roleClassification`, `skillGaps`. Scores are unchanged.

**Match source labels (UI):**

| `matchSource` | UI label | Meaning |
|---------------|----------|---------|
| `embeddings` | Embeddings | Scored by embeddings only |
| `embeddings+llm` | Embeddings + AI | Embeddings + LLM explanations |
| `ml` | ML fallback | TF-IDF/keyword heuristic (embedding model unavailable) |

**API response:** `matchingPipeline` object includes `steps`, `llmUsed`, `embeddingsUsed`, `embeddingModel`, `llmProvider`, `matchSource`, and `message`. The Results tab pipeline banner reads this object.

##### Path C — CV Analyzer and Tailor (no LLM)

**Analyze** (`POST /api/job-automation/analyze`) and **Tailor** (`POST /api/job-automation/resume/tailor`) do **not** call `invoke_llm()`.

They use **keyword overlap heuristics** in `analyze_job()`:

- Compare CV skills vs job description text
- Compute `hits`, `misses`, `skillGaps`, and a heuristic `score`
- **Tailor** assembles a template resume string from analyze output

Despite UI labels like "AI" in some areas, these two flows are rule-based in the current implementation.

##### Embeddings vs LLM — responsibility matrix

| Component | Role | Uses LLM? |
|-----------|------|-----------|
| `embedding_service.py` | Primary job match **scores** | No |
| `job_match_ai._embedding_job_score()` | Score and sort jobs | No |
| `job_match_ai._llm_explain_jobs()` | Explanations, gaps, role class | Yes (optional) |
| `resume_ai._ml_skill_assessment()` | Resume role-fit score | No |
| `resume_ai._langchain_agent_assessment()` | Resume parse insights | Yes (optional) |
| `analyze_job()` / `tailor_resume_for_job()` | Single-job analysis and tailoring | No |

##### Typical Auto Apply journey

1. **Profile:** Upload one or more resumes → Parse with AI (sequential, isolated snapshots) → set Active CV → profile populated
2. **Portals:** Add LinkedIn or other portal URLs (Excel import skips rows without valid URLs)  
3. **Job Search or Profile:** Configure titles (search tags or profile job titles), skills, min match %
4. **Auto Apply:** Scrape → prefilter → embed-rank → optional LLM explain → apply to jobs above threshold (up to `maxApplications`, default 20)
5. **Results:** Ranked jobs with `match %`, `matchInsight`, `skillGaps`, and pipeline banner

##### Enable LLM reasoning

Add to `backend/.env`:

```env
USE_LOCAL_LLM=true
OLLAMA_MODEL=mistral
OLLAMA_BASE_URL=http://localhost:11434

# Optional — force LLM on every resume parse (otherwise auto when Ollama/OpenAI is up)
RESUME_PARSE_INCLUDE_LLM=true
RESUME_PARSE_LLM_TIMEOUT_SECONDS=30

# Fast local embeddings (skip Hugging Face download)
EMBEDDING_BACKEND=sklearn_tfidf

# Live LinkedIn scraping (optional)
APIFY_API_TOKEN=your_apify_token
USE_APIFY_SCRAPER=true

# OpenAI fallback when Ollama is down
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4o-mini
```

Start Ollama before demos:

```bash
ollama run mistral
```

**Without LLM:** embeddings still rank jobs; resume parse still works via rules + ML; only explanations and resume LLM insights are skipped. The UI shows an embeddings-only pipeline banner with guidance to start Ollama or set `OPENAI_API_KEY`.

##### Frontend timeouts

Long-running Job Automation and AI calls use a **240 second** Axios timeout (`LONG_RUNNING_TIMEOUT_MS` in `frontend/src/api/client.js`) for resume parse, search run, auto apply, and LinkedIn operations. The default timeout for other API calls is **30 seconds**.

### 10.4 LinkedIn Recruiter

**Route:** `/linkedin`

**Tabs:** Discover · Paste Profiles · API Sources · AI Outreach · Sequence Tracker · Settings

| Tab | Actions |
|-----|---------|
| Discover | Filter by company, technology, seniority, location, connections; run searches; **Save** (bookmark) recruiters to your list per card |
| Paste Profiles | Paste LinkedIn URLs for enrichment, or **Import CSV** to extract and enrich LinkedIn profile URLs in bulk |
| API Sources | View Apollo, Hunter, RocketReach, Lusha connection status |
| AI Outreach | Generate messages; rich-text editor with bold, italic, bullet **and numbered lists**, and **insert link**; pick a **schedule date/time**; **Save Template** to persist a reusable message |
| Sequence Tracker | Monitor queued/sent outreach steps |
| Settings | API keys, daily connection/InMail limits (admin+) |

**Recruiter actions (Discover cards):** Connect · Message · Email · **Save** (bookmark). Saving toggles the recruiter's `bookmarked` flag and persists it (`PUT /api/linkedin/recruiters/{id}/bookmark`), so saved recruiters survive reloads.

**CSV import (Paste Profiles):** Click **Import CSV** and choose a `.csv` file (≤ 2 MB). The app extracts up to 100 unique LinkedIn profile URLs from the file, populates the paste box, and runs enrichment automatically.

**AI Outreach editor & scheduling:**

| Control | Behavior |
|---------|----------|
| Toolbar | Bold, italic, bullet list, **numbered list**, **insert link** (validates `http(s)` only) |
| Schedule date/time | `datetime-local` picker (defaults to tomorrow 09:00); **Schedule** queues delivery for the chosen future time |
| Save Template | Prompts for a template name and persists the current editor body (`POST /api/linkedin/templates`); saved templates appear in **Saved Message Templates** and survive reloads |

Scheduled outreach and Save Template writes require **admin** or **super_admin**; scheduled sends are stored in the `linkedin_outreach_queue` table and rejected if the chosen time is in the past.

**LinkedIn message types:**

| Type | Use case |
|------|----------|
| `connect` | Connection request note |
| `inmail` | LinkedIn InMail introduction |
| `cold_outreach` | Cold recruiter outreach |
| `followup` | Follow-up on prior message |
| `hotlist` | Bench hotlist share |
| `thankyou` | Post-connection thank you |
| `resume` | Resume share follow-up |

Outreach queue actions require **admin** or **super_admin**.

### 10.5 Day Report

**Route:** `/day-report`

The dashboard auto-loads the **last 30 days** on open via `POST /api/day-report/filter`.

**KPI definitions:**

| Metric | Description |
|--------|-------------|
| LinkedIn | LinkedIn activity count (messages, connections, profile views) |
| Calls | Phone calls made |
| Sourced | Profiles sourced for open roles |
| Marketing | Marketing outreach actions |

**Charts and tables:**

- Daily trend line chart (Sourced / Calls with point markers; LinkedIn dotted, Marketing dashed) with an X-axis cursor and date-labeled tooltip
- Totals by recruiter (bar chart)
- Metric mix (stacked bar by day)
- Breakdown by technology (full tech field, not comma-split)
- Filterable detail table by date range and recruiter
- **Apply** / **Reset** filter controls with summary totals

**Date filtering:**

- Both start and end dates are optional. Leave either side blank for an **open-ended range** (e.g. everything up to an end date, or everything from a start date). If both are entered, start must be on or before end.

**Weekend / holiday / leave rows:**

- Activity metrics (LinkedIn, Calls, Sourced, Marketing) are **nullable**. Rows with no recorded activity (e.g. weekend, holiday, or leave entries) display a dash (`-`) in the detail table instead of `0`, while KPI totals and charts still treat missing values as `0`.

### 10.6 Submissions

**Route:** `/submissions`

- Filter by **start month** and **end month** (calendar inputs) via `POST /api/submissions/filter`
- **Apply** / **Reset** controls
- MoM **bar** chart and YoY **line** chart
- Calendar **heatmap** by submission volume
- Summary: total submissions, monthly average, and per-month delta pills
- Positive/negative trend indicators per month

### 10.7 API Explorer

**Route:** `/api-explorer`

- Fetches live endpoint catalog from `/api/meta/endpoints`
- Shows method, path, summary, request example, and response example per endpoint
- Direct links to Swagger docs and OpenAPI JSON

### 10.8 My Profile (account settings)

**Route:** `/profile`

This is the **account** profile (login user settings). It is **not** the Job Automation multi-CV / multi-profile library — that lives under Job Automation → **My Profile** ([§10.3.1](#1031-my-profile-multi-profile--multi-cv)).

**Tabs:** Profile · Settings · Notifications · Password

| Tab | Fields / toggles |
|-----|------------------|
| Profile | Name, phone, company, title, department, location, timezone, bio |
| Settings | Language, date format, theme |
| Notifications | Email, campaign alerts, job alerts, daily report, weekly digest, **SMS** toggle + phone, test send buttons, delivery history |
| Password | Current, new, confirm (demo stub) |

---

## 11. Backend API Reference

All protected endpoints require:

```
Authorization: Bearer <token>
```

Obtain a token via `POST /api/auth/login`.

### 11.1 Authentication

| Method | Endpoint | Access |
|--------|----------|--------|
| GET | `/api/auth/options` | Public |
| POST | `/api/auth/login` | Public |
| POST | `/api/auth/register` | Public |
| POST | `/api/auth/logout` | Authenticated |
| GET | `/api/auth/me` | Authenticated |

### 11.2 User Profile

| Method | Endpoint | Access |
|--------|----------|--------|
| GET | `/api/user/profile` | Authenticated |
| PUT | `/api/user/profile` | Authenticated |
| PUT | `/api/user/password` | Authenticated |
| GET | `/api/user/settings` | Authenticated |
| PUT | `/api/user/settings` | Authenticated |

### 11.3 Notifications (email & SMS)

| Method | Endpoint | Access |
|--------|----------|--------|
| GET | `/api/notifications/setup` | user, admin, super_admin |
| GET | `/api/notifications/history` | user, admin, super_admin |
| POST | `/api/notifications/test-email` | user, admin, super_admin |
| POST | `/api/notifications/test-sms` | user, admin, super_admin |

**Automatic events:** job auto-apply (email + SMS when alerts enabled), campaign launch (email when campaign alerts enabled).

### 11.4 Health and Overview

| Method | Endpoint | Access |
|--------|----------|--------|
| GET | `/health` | user, admin, super_admin |
| GET | `/api/overview` | user, admin, super_admin |

### 11.5 Campaigns

| Method | Endpoint | Access |
|--------|----------|--------|
| GET | `/api/campaigns/workspace` | All roles |
| POST | `/api/campaigns/preview` | All roles |
| POST | `/api/campaigns/test-send` | admin, super_admin |
| POST | `/api/campaigns/launch` | admin, super_admin |
| POST | `/api/campaigns/drafts` | admin, super_admin |
| POST | `/api/campaigns/contacts/import` | admin, super_admin |
| POST | `/api/campaigns/test-smtp` | admin, super_admin |
| PUT | `/api/campaigns/settings` | admin, super_admin |
| POST | `/api/campaigns/lists` | admin, super_admin |

### 11.6 Job Automation

| Method | Endpoint | Access |
|--------|----------|--------|
| GET | `/api/job-automation/workspace` | All roles |
| PUT | `/api/job-automation/profile` | user, admin, super_admin |
| PUT | `/api/job-automation/automation` | user, admin, super_admin |
| PUT | `/api/job-automation/search` | user, admin, super_admin |
| POST | `/api/job-automation/search/run` | user, admin, super_admin |
| POST | `/api/job-automation/portals` | admin, super_admin |
| DELETE | `/api/job-automation/portals` | admin, super_admin |
| POST | `/api/job-automation/portals/import` | admin, super_admin |
| POST | `/api/job-automation/carriers` | admin, super_admin |
| DELETE | `/api/job-automation/carriers` | admin, super_admin |
| POST | `/api/job-automation/carriers/import` | admin, super_admin |
| POST | `/api/job-automation/apply` | user, admin, super_admin — body `{ jobIds, supervised? }`; returns applications + `supervised` flag |
| GET | `/api/job-automation/applications` | user, admin, super_admin — list tracker rows |
| GET | `/api/job-automation/applications/{application_id}` | user, admin, super_admin — poll apply status (`attemptStatus`: queued/filling/needs_attention/awaiting_submit/applied/failed/manual) |
| POST | `/api/job-automation/auto-apply` | user, admin, super_admin |
| POST | `/api/job-automation/analyze` | All roles |
| POST | `/api/job-automation/save` | All roles |
| POST | `/api/job-automation/resume/parse` | All roles (multipart) — parse one file; stores isolated `profile_snapshot`; makes it Active |
| GET | `/api/job-automation/resumes` | All roles — lists the user's CV library (each item may include `profileSnapshot`, `profileName`, `experience`) |
| POST | `/api/job-automation/resumes/{resume_id}/activate` | All roles — switches Active CV and reloads that CV’s full snapshot into `profile` + `search` |
| DELETE | `/api/job-automation/resumes/{resume_id}` | All roles — removes a CV; if it was Active, newest remaining becomes Active and hydrates profile |
| PUT | `/api/job-automation/profile` | user, admin, super_admin — saves Active working copy and syncs Active CV’s `profile_snapshot` only |
| POST | `/api/job-automation/resume/tailor` | All roles |
| POST | `/api/job-automation/resume/save-tailored` | All roles |
| GET | `/api/job-automation/resume/tailored/{job_id}` | All roles |
| POST | `/api/job-automation/linkedin/search` | All roles |
| POST | `/api/job-automation/linkedin/apply` | admin, super_admin |

**Resume parse form fields:**

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `file` | Yes | — | Resume file (.txt, .pdf, .docx) |
| `targetRole` | No | `Software Engineer` | Role used for match scoring |
| `requiredSkills` | No | `Python, FastAPI, SQL` | Comma-separated skills |

**Resume parse response** includes `parsedProfile`, `mlAssessment`, `llmAssessment`, `agentTrace`, plus updated `profile`, `search`, and `resumes` (the user's full CV library) when persistence succeeds. Each CV in `user_resumes` stores file bytes, summary, skills, job titles, ML assessment, and an isolated **`profile_snapshot`** (contact + prefs + resume fields). Parse **replaces** the Active working profile/search from that snapshot only — it does not merge skills across CVs. Activate returns the restored `profile` and `search` for the selected CV.

**Search / auto-apply response** includes `results`, `scrapedCount`, `portalsScraped`, and `matchingPipeline` (`steps`, `llmUsed`, `embeddingsUsed`, `embeddingModel`, `llmProvider`, `matchSource`, `message`). Each result's `sourceUrl` is a sanitized portal posting/search URL (Dice, Monster, CareerBuilder, LinkedIn, Indeed, ZipRecruiter). **Quick Apply** (`POST /apply` with `supervised: true`) launches portal automation and returns application rows with `jobResultId`, `attemptStatus`, and `attemptDetail` for Results-tab polling. `search/run` and `apply` are scoped to the calling user's own job results.

**Search save body** (`PUT /api/job-automation/search`): `titles`, `requiredSkills`, `optionalSkills`, `location`, `radius`, `filters`, `excludeKeywords`, `employmentType`, `minMatchScore`, `postedWithin`, `experienceLevel`, `rateMin`, `rateMax`, `repeatEvery`.

### 11.7 LinkedIn Recruiter

| Method | Endpoint | Access |
|--------|----------|--------|
| GET | `/api/linkedin/workspace` | All roles |
| POST | `/api/linkedin/discover` | All roles |
| POST | `/api/linkedin/enrich` | All roles |
| PUT | `/api/linkedin/recruiters/{id}/bookmark` | user, admin, super_admin |
| POST | `/api/linkedin/outreach` | admin, super_admin |
| POST | `/api/linkedin/outreach/generate` | All roles |
| POST | `/api/linkedin/templates` | admin, super_admin |
| PUT | `/api/linkedin/settings` | admin, super_admin |
| PUT | `/api/linkedin/api-keys` | admin, super_admin |

**Bookmark body** (`PUT /api/linkedin/recruiters/{id}/bookmark`): `{ "bookmarked": true | false }`. Returns `{ success, message }`; the recruiter's `bookmarked` flag is reflected in the workspace response.

**Template body** (`POST /api/linkedin/templates`): `{ "name": string (2–120), "body": string (1–5000) }`. Creating a template with an existing name updates it; returns `{ id, name, body }`.

**Outreach body** (`POST /api/linkedin/outreach`) accepts an optional `scheduleAt` ISO-8601 datetime. When provided it must include a timezone and be in the future; scheduled sends are persisted to `linkedin_outreach_queue`.

### 11.8 Day Report

| Method | Endpoint | Access |
|--------|----------|--------|
| GET | `/api/day-report/dashboard` | All roles |
| POST | `/api/day-report/filter` | All roles |

### 11.9 Submissions

| Method | Endpoint | Access |
|--------|----------|--------|
| GET | `/api/submissions/dashboard` | All roles |
| POST | `/api/submissions/filter` | All roles |

### 11.10 Meta / Test Data

| Method | Endpoint | Access |
|--------|----------|--------|
| GET | `/api/meta/endpoints` | All roles |
| GET | `/api/meta/test-data` | admin, super_admin |
| POST | `/api/meta/test-data/append` | super_admin only |
| POST | `/api/meta/test-data/reset` | super_admin only |

---

## 12. Swagger API Usage

1. Open http://127.0.0.1:8000/docs
2. Click **Authorize** and enter: `Bearer <your-token>`
3. Expand any endpoint → **Try it out** → fill parameters → **Execute**
4. Inspect the status code and response body

To get a token quickly, log in via the web app and copy from browser dev tools, or call `POST /api/auth/login` in Swagger.

---

## 13. Test Data Operations

Super admins can mutate seed data for demos and testing. These operations are available via **curl**, **Swagger**, or **API Explorer** — there is no dedicated UI button yet.

### 13.1 Appendable Datasets

| Dataset key | Contents |
|-------------|----------|
| `campaign_contacts` | Email campaign contacts |
| `campaign_templates` | Email templates |
| `campaign_lists` | Contact list definitions |
| `campaign_items` | Campaign run records |
| `portal_items` | Job portal URLs |
| `carrier_items` | Carrier site entries |
| `day_report_rows` | Daily recruiter activity rows |
| `job_results` | Job search results |
| `search_configs` | Job search title/skill/filter configuration |
| `job_profiles` | Candidate profile rows |
| `linkedin_jobs` | LinkedIn job listings |
| `applications` | Job application tracker rows |
| `submission_months` | Monthly submission totals |

### 13.2 Export Current Runtime Dataset

```bash
curl -s http://127.0.0.1:8000/api/meta/test-data \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 13.3 Append Rows to a Dataset

```bash
curl -s -X POST http://127.0.0.1:8000/api/meta/test-data/append \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "campaign_contacts",
    "entries": [
      {
        "name": "Priya N",
        "email": "priya@example.com",
        "company": "Acme",
        "status": "Queued",
        "list": "Priority Accounts"
      }
    ]
  }'
```

### 13.4 Reset Runtime Dataset to Baseline

```bash
curl -s -X POST http://127.0.0.1:8000/api/meta/test-data/reset \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 14. PostgreSQL Database Schema

MarketingMind AI includes a full **PostgreSQL** schema (32 tables) defined in `backend/app/db/models.py`. The schema mirrors all major modules: auth, campaigns, job automation, LinkedIn recruiter, reporting, and notifications.

### 14.1 Local connection

| Setting | Value |
|---------|-------|
| Host | `localhost` |
| Port | `5432` |
| Database | `postgres` |
| Username | `postgres` |
| Password | `admin` |
| SQLAlchemy URL | `postgresql+psycopg://postgres:admin@localhost:5432/postgres` |

Set in `backend/.env`:

```env
DATABASE_URL=postgresql+psycopg://postgres:admin@localhost:5432/postgres
USE_SEED_DATA=false
```

### 14.2 Initialize schema and seed data

From `backend/` with PostgreSQL running:

**macOS / Linux:**

```bash
python scripts/init_postgres_schema.py
```

**Windows (PowerShell):**

```powershell
python scripts/init_postgres_schema.py
```

This script:

1. Creates all 32 tables via SQLAlchemy `create_all`
2. Seeds demo users, campaigns, job automation, LinkedIn, and reporting data from `app/data/test_data.json`
3. Prints a summary of tables created

Re-run the script to reset PostgreSQL to the baseline seed (drops and recreates tables).

### 14.3 Table groups (32 tables)

| Group | Tables |
|-------|--------|
| **Auth & users** | `users`, `user_settings`, `auth_sessions` |
| **Campaigns** | `campaign_settings`, `contact_lists`, `campaign_contacts`, `campaign_templates`, `campaign_items` |
| **Job automation** | `job_profiles`, `user_resumes`, `job_automation_settings`, `search_configs`, `portals`, `carriers`, `job_results`, `saved_jobs`, `job_applications`, `tailored_resumes`, `linkedin_jobs`, `job_analyses` |
| **LinkedIn recruiter** | `linkedin_recruiters`, `linkedin_sequences`, `linkedin_sequence_steps`, `linkedin_followups`, `linkedin_message_templates`, `linkedin_outreach_queue`, `linkedin_settings`, `linkedin_api_sources`, `linkedin_api_keys` |
| **Reporting** | `day_report_rows`, `submission_months` |
| **Notifications** | `notification_deliveries` |

> **Schema notes:** `user_resumes.profile_snapshot` (JSONB) holds the isolated multi-profile fields per CV; `is_active` marks the single Active CV. `job_profiles` remains the denormalized Active working copy for apply/search. `linkedin_recruiters` includes a `bookmarked` boolean (save-to-list). `linkedin_outreach_queue` stores scheduled outreach (recruiter IDs, subject, body, channel, `scheduled_for`, status). `day_report_rows` activity metrics (`linkedin`, `calls`, `sourced`, `marketing`) are **nullable** to support weekend/holiday/leave rows. Existing PostgreSQL databases are patched automatically on startup (add `bookmarked`, `profile_snapshot`, drop `NOT NULL` on the four metrics).

Full column-level documentation: `backend/database/SCHEMA.md` · DDL: `backend/database/schema.sql`

### 14.4 Runtime data path

| Layer | Status |
|-------|--------|
| PostgreSQL (`DATABASE_URL` set, `USE_SEED_DATA=false`) | **Primary** — `pg_store` handles campaigns, job automation, LinkedIn, reporting, auth |
| JSON seed (`USE_SEED_DATA=true` or no DB) | Fallback — read/write `backend/app/data/test_data.json` |
| Backend startup | Runs `create_all` on SQLAlchemy models when `DATABASE_URL` is set; warms embedding backend |

Job Automation **Parse with AI** persists an isolated CV snapshot plus the Active working profile/search to PostgreSQL (`user_resumes.profile_snapshot`, `job_profiles`, `search_configs`) when the database is available. Activating another CV reloads that snapshot into `job_profiles` without merging other CVs.

### 14.5 Verify PostgreSQL

```powershell
# List tables (psql)
psql -U postgres -h localhost -d postgres -c "\dt"

# Or check health endpoint after login
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Headers @{ Authorization = "Bearer YOUR_TOKEN" }
```

Health `database` field reports `available`, `not_configured`, or `error`.

---

## 15. Configuration Reference

### 15.1 PostgreSQL

```env
DATABASE_URL=postgresql+psycopg://postgres:admin@localhost:5432/postgres
```

PostgreSQL is the default database. Run `scripts/init_postgres_schema.py` once after setup. Health endpoint `database` field reports `available`, `not_configured`, or `error`.

### 15.2 Campaign SMTP (Optional)

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM_EMAIL=your_email@gmail.com
CAMPAIGN_FORCE_DEMO_MODE=false
CAMPAIGN_SENDER_LIMIT=500
CAMPAIGN_EMAIL_DELAY_SECONDS=1
```

When SMTP is configured and demo mode is off, campaign launch sends real email with merge tags. Use **Test SMTP** in Campaign Studio Settings or `POST /api/campaigns/test-smtp` to verify.

### 15.3 OpenAI / Local LLM / Embeddings (Optional)

**Local LLM (recommended for dev):**

```env
USE_LOCAL_LLM=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral
OLLAMA_TIMEOUT_SECONDS=120
RESUME_PARSE_INCLUDE_LLM=false
RESUME_PARSE_LLM_TIMEOUT_SECONDS=10
```

Run `ollama run mistral` before using LLM features. Resume parse auto-enables LLM when Ollama (or OpenAI) is reachable even if `RESUME_PARSE_INCLUDE_LLM=false`.

**OpenAI fallback:**

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
```

**Embeddings (primary job matcher — no API key required):**

```env
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_BACKEND=sklearn_tfidf
```

Use `EMBEDDING_BACKEND=sentence_transformers` for higher-quality MiniLM embeddings (slower first startup). Default `sklearn_tfidf` avoids Hugging Face download on cold start.

Without Ollama or OpenAI, resume parsing still returns rule-based extraction and ML scoring; job search still ranks via embeddings.

### 15.4 Live Job Scraping

Dice live scraping is enabled by default and requires no API key:

```env
DICE_LIVE_SCRAPING_ENABLED=true
DICE_SCRAPE_TIMEOUT_SECONDS=15
DICE_JOBS_PER_SEARCH=10
```

The Dice request uses the Job Search location, posted-date setting, and first AI/resume keyword. Example: `https://www.dice.com/jobs?filters.postedDate=THREE&countryCode=US&location=Dallas%2C+TX&q=Java`. The scraper extracts real job-detail URLs from Dice's server-rendered Next.js payload. If Dice is unavailable or its response changes, the app logs a warning and uses generated fallback jobs instead of failing the search.

The same normalized keyword, location, and posted-date settings are applied with each portal's supported URL format: CareerBuilder (`posted`), LinkedIn (`f_TPR`), Indeed (`fromage`), and ZipRecruiter (`days`). Monster receives keyword, location, and page parameters; its public URL has no stable date parameter, so posted-date filtering is enforced by the backend. Unknown custom portals receive generic `q`, `location`, `postedWithin`, and `countryCode` parameters. Apify LinkedIn URLs also receive `f_TPR`.

Apify is optional and provides live LinkedIn scraping:

```env
APIFY_API_TOKEN=your_apify_token
USE_APIFY_SCRAPER=true
APIFY_ACTOR_ID=curious_coder/linkedin-jobs-scraper
APIFY_JOBS_PER_SEARCH=25
```

When `APIFY_API_TOKEN` is empty, LinkedIn portals use simulated scrape data. See [Apify Job Scraping API](https://apify.com/api/job-scraping-api).

### 15.5 Supervised Quick Apply (Playwright)

True portal apply for Dice, CareerBuilder, Monster, Indeed, ZipRecruiter, and LinkedIn:

```env
PORTAL_APPLY_MODE=supervised
PORTAL_APPLY_TIMEOUT_SECONDS=600
PORTAL_APPLY_PROFILE_DIR=.playwright/dice-profile
PLAYWRIGHT_HEADLESS=false
PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers
PORTAL_APPLY_AUTO_SUBMIT=true
```

| Mode | Behavior |
|------|----------|
| `supervised` | Headed Chromium fills + submits (pause for login/CAPTCHA) |
| `manual` | Opens posting URL; tracker marks for manual completion |
| `demo` | Marks **Applied** without opening a browser (CI/tests) |

Install Chromium once: `pip install playwright` then `playwright install chromium` (browsers path above). Per-portal browser profiles are stored under `.playwright/{portal}-profile/`.

### 15.6 Third-Party API Keys (Optional)

Configure in `backend/.env` or via LinkedIn Recruiter **Settings** tab:

```env
APOLLO_API_KEY=
HUNTER_API_KEY=
LINKEDIN_API_KEY=
```

### 15.7 Frontend API URL (Deployment)

```env
VITE_API_BASE_URL=https://api.yourdomain.com
```

Rebuild the frontend (`npm run build`) after changing this value.

---

## 16. Build and Validation

### 16.1 Frontend Production Build

```bash
cd frontend
npm run build
npm run preview    # serve dist/ locally for smoke testing
```

Output is written to `frontend/dist/`.

### 16.2 Lint Frontend

```bash
cd frontend
npm run lint
```

### 16.3 Backend Health Smoke Check

**macOS / Linux:**

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@marketingmind.ai","password":"Admin@123"}' | jq -r '.token')

curl -s http://127.0.0.1:8000/health -H "Authorization: Bearer $TOKEN"
```

**Windows (PowerShell):**

```powershell
$login = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/auth/login" `
  -Method POST -ContentType "application/json" `
  -Body '{"email":"admin@marketingmind.ai","password":"Admin@123"}'

Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" `
  -Headers @{ Authorization = "Bearer $($login.token)" }
```

### 16.4 Resume Parse API Smoke Check

Create `resume_sample.txt`, then:

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@marketingmind.ai","password":"Admin@123"}' | jq -r '.token')

curl -s -X POST http://127.0.0.1:8000/api/job-automation/resume/parse \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@resume_sample.txt;type=text/plain" \
  -F "targetRole=Backend Engineer" \
  -F "requiredSkills=Python,FastAPI,SQL,AWS,Docker"
```

### 16.5 Automated Test Suites

Install backend test dependencies once:

```bash
cd backend
.venv\Scripts\pip.exe install -r requirements-dev.txt   # Windows
pip install -r requirements-dev.txt                    # macOS/Linux
```

Run all tests:

```bash
# Backend — 113 pytest tests
cd backend && .venv\Scripts\python.exe -m pytest -q

# Frontend — 25 vitest tests
cd frontend && npm test
```

Current suite: **113 backend + 25 frontend = 138 automated tests**.

Full details: `docs/TESTING_GUIDE.md` and `backupfolder/FUNCTIONAL_TEST_CASES.md`.

---

## 17. Troubleshooting

### 17.1 `uvicorn: command not found`

Activate the venv and use `python -m uvicorn` (see Section 7.1). On Windows you can skip activate: `.\.venv\Scripts\python.exe -m uvicorn ...`.

### 17.2 Virtual environment not found

Run setup from `backend/` and confirm `.venv` exists before activating.

### 17.3 `Address already in use` (port 8000, 8002, or 5173)

**macOS / Linux:**

```bash
lsof -nP -iTCP:8002 -sTCP:LISTEN
lsof -tiTCP:8002 -sTCP:LISTEN | xargs kill -9
```

**Windows (PowerShell):**

```powershell
foreach ($port in @(5173, 8002)) {
  Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}
```

Use `8000` instead of `8002` if that is the API port. Repeat for `5173` if Vite cannot bind. Then follow Section 7.1 and 7.2.

### 17.4 Session expired / 401 errors

Log out and log in again. Sessions are stored in PostgreSQL (`auth_sessions`) and use **sliding expiry** — every authenticated request from an active user renews the session, so 401s normally only occur after long inactivity (default lifetime `JWT_EXPIRATION_HOURS`, 24h) or after the session row is deleted.

### 17.5 Swagger returns 401

Use **Authorize** with `Bearer <token>` from a successful login.

### 17.6 `pip install` timeout

```bash
cd backend
python -m pip install --default-timeout=180 -r requirements.txt
```

### 17.7 Frontend cannot reach API

1. Backend is running (Swagger opens on the same host/port as `VITE_API_BASE_URL`)
2. `VITE_API_BASE_URL` matches backend URL exactly (8000 vs 8002)
3. Restart Vite after changing `frontend/.env`
4. `ALLOWED_ORIGINS` includes `http://localhost:5173`

### 17.8 `SettingsError` for `allowed_origins`

`ALLOWED_ORIGINS` must be valid JSON array syntax in `.env`, not a plain comma-separated string:

```env
# Correct
ALLOWED_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]

# Wrong
ALLOWED_ORIGINS=http://localhost:5173
```

### 17.9 PostgreSQL connection errors

1. Confirm PostgreSQL is running on `localhost:5432`
2. Verify credentials match `DATABASE_URL` (`postgres` / `admin`)
3. Run `python scripts/init_postgres_schema.py` from `backend/`
4. Check health endpoint `database` field after login

### 17.10 Auto apply shows no results

1. Portals are **auto-seeded** (Dice, Monster, CareerBuilder) on first workspace load — you can add more in **Portals**
2. Add job titles in **Job Search** or parse a resume on **My Profile** (titles sync to search)
3. Lower the **Minimum match score** slider on Results if jobs were ranked below the default filter
4. Check the pipeline banner on **Results** for scrape/ranking messages

### 17.11 LinkedIn page shows empty data

Click into **LinkedIn Recruiter** from the sidebar — it loads `/api/linkedin/workspace` on page mount, separate from the main workspace refresh.

---

## 18. Known Limitations

| Area | Current behavior |
|------|------------------|
| Data persistence | PostgreSQL via `pg_store` when `DATABASE_URL` is set; JSON seed fallback when `USE_SEED_DATA=true` |
| Test data UI | Append/reset available via API only (no admin UI panel) |
| Auth | Demo accounts with seeded passwords — harden for production |
| Registration | Any role can be selected at signup (demo only) |
| Password change | Stub endpoint; no real hash verification |
| SMTP / LinkedIn outreach | Live when configured; otherwise simulated delivery |
| LinkedIn / job boards | Simulated scrape unless `APIFY_API_TOKEN` is set; CV ↔ job ranking uses local embeddings; optional Ollama/OpenAI for explanations only |
| CV Analyzer / Tailor | Keyword heuristics — not LLM-backed in current code |

---

## 19. Operational Recommendations

1. Keep backend and frontend in separate terminals for clean logs.
2. Use fixed ports (`8000`, `5173`) for stable local routing.
3. Use `--strictPort` on the frontend to avoid silent port changes.
4. Run `init_postgres_schema.py` once after PostgreSQL is installed.
5. Use **API Explorer** to keep UI actions aligned with the backend contract.
6. Use **Swagger** to validate requests before wiring new UI features.
7. Reset test data after experiments for deterministic demo behavior.
8. Log in as **super_admin** only when you need to append or reset seed data.
9. Run `ollama run mistral` (or set `OPENAI_API_KEY`) before demoing LLM ranking explanations; embeddings work without any API key.
10. Log in as **user** to test profile, auto-apply, and per-user workspace scoping; use **admin** for portal CRUD and campaign launch.
11. Run `pytest` and `npm test` before releases (see Section 21).

---

## 20. Quick Start Checklist

- [ ] Install PostgreSQL 14+ and confirm it runs on `localhost:5432`
- [ ] Create backend venv and `pip install -r requirements.txt`
- [ ] Copy `backend/.env.example` → `backend/.env` (set `DATABASE_URL`, `USE_SEED_DATA=false`)
- [ ] Run `python scripts/init_postgres_schema.py` from `backend/`
- [ ] `npm install` in `frontend/` and copy `frontend/.env.example` → `frontend/.env`
- [ ] Start backend on `127.0.0.1:8000` (or `8002` if port busy — update `VITE_API_BASE_URL`)
- [ ] Start frontend on `localhost:5173` with `--strictPort`
- [ ] Log in with a demo account (or click a Demo User card)
- [ ] Verify Command Center loads with module cards and metrics
- [ ] Open Job Automation → **My Profile** → multi-select resumes → **Parse with AI** (sequential)
- [ ] Confirm CV library shows multiple CVs; **Set active** reloads that CV’s isolated contact/skills
- [ ] Edit Active profile → **Save active profile** → switch Active to another CV and confirm edits did not leak
- [ ] **Run auto apply now** on My Profile → confirm **Results** tab (portals auto-seeded; uses Active CV)
- [ ] Open LinkedIn Recruiter and confirm workspace loads
- [ ] Run `pytest -q` (backend) and `npm test` (frontend) — expect **138** passing tests
- [ ] Quick Apply a Dice / CareerBuilder / Monster result → Results card shows **Applied**
- [ ] Open API Explorer and confirm endpoint catalog loads
- [ ] Open Swagger and test one authenticated endpoint

---

## 21. Automated Testing & QA

MarketingMind AI ships with **138 automated tests** mapped to manual functional test cases.

| Layer | Location | Command |
|-------|----------|---------|
| Backend API | `backend/tests/test_functional_*.py` | `cd backend && .venv\Scripts\python.exe -m pytest -q` |
| Backend unit | `backend/tests/test_reporting_helpers.py` | same |
| Backend notifications | `backend/tests/test_functional_notifications.py` | same |
| Frontend | `frontend/src/utils/*.functional.test.js` | `cd frontend && npm test` |

**Manual functional tests:** `backupfolder/FUNCTIONAL_TEST_CASES.md` — covers legacy HTML prototypes (Job Automation, Campaigns, Day Report, LinkedIn, Submissions).

**Full testing guide:** `docs/TESTING_GUIDE.md`

---

## 22. Production Logging

### Backend

Structured logging is configured in `backend/app/core/logging.py` and request middleware in `backend/app/core/middleware.py`.

| Setting | Purpose |
|---------|---------|
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `ENVIRONMENT=production` | Emits JSON-formatted logs for aggregators (timestamp, level, logger, message, request fields) |

Access logs include method, path, status code, and duration. Auto-apply and other critical flows log success/failure with user context.

### Frontend

Client logging uses `frontend/src/utils/logger.js` with the `[MM]` prefix.

| Setting | Purpose |
|---------|---------|
| `VITE_LOG_LEVEL` | `debug`, `info`, `warn`, `error` (default: `debug` in dev, `warn` in production builds) |

API errors are logged via `client.js`; unhandled React errors are caught by `ErrorBoundary.jsx`.

---

## 23. Notifications, Email & SMS

### 23.1 Overview

| Channel | Use case | Configuration |
|---------|----------|---------------|
| **Campaign SMTP** | Mass email campaigns (Campaign Studio) | `SMTP_*` in `.env` or Campaign Settings tab |
| **Transactional email** | Profile alerts, job auto-apply, campaign summaries | Same SMTP + `NOTIFICATION_FROM_*` |
| **SMS** | Job automation alerts | `SMS_PROVIDER=twilio` + Twilio credentials |

Without SMTP/Twilio credentials, channels run in **demo mode** (logged, not sent externally).

### 23.2 User preferences (`/profile` → Notifications)

| Toggle | Triggers |
|--------|----------|
| Email Notifications | Master switch for transactional email |
| Campaign Alerts | Email when campaigns are sent/scheduled |
| Job Alerts | Email/SMS on auto-apply completion |
| SMS Notifications | SMS for job automation events |
| Daily Report / Weekly Digest | Scheduled summary emails (when scheduler enabled) |

Use **Send test email** and **Send test SMS** to verify setup. Delivery history appears below the save button.

### 23.3 Backend configuration

```env
# Campaign + notification email (shared SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your@email.com
SMTP_PASSWORD=app-password
SMTP_FROM_EMAIL=your@email.com
CAMPAIGN_FORCE_DEMO_MODE=false

# Transactional notifications
NOTIFICATION_FROM_NAME=MarketingMind AI
NOTIFICATION_FROM_EMAIL=
NOTIFICATION_FORCE_DEMO_MODE=false

# SMS (optional)
SMS_PROVIDER=twilio
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
```

### 23.4 API quick reference

| Action | Endpoint |
|--------|----------|
| Channel status | `GET /api/notifications/setup` |
| Delivery log | `GET /api/notifications/history` |
| Test email | `POST /api/notifications/test-email` |
| Test SMS | `POST /api/notifications/test-sms` |
| Test campaign SMTP | `POST /api/campaigns/test-smtp` |

---

## 24. Related Documentation

| Document | Description |
|----------|-------------|
| [`usermanual.mfd`](usermanual.mfd) | JSON documentation manifest (paths, versions, test counts) |
| [`docs/DOCUMENTATION_INDEX.md`](docs/DOCUMENTATION_INDEX.md) | Human-readable index of all docs |
| [`docs/TESTING_GUIDE.md`](docs/TESTING_GUIDE.md) | Test suite layout and CI notes |
| [`backupfolder/FUNCTIONAL_TEST_CASES.md`](backupfolder/FUNCTIONAL_TEST_CASES.md) | Manual + automated functional test mapping |
| [`backend/database/SCHEMA.md`](backend/database/SCHEMA.md) | PostgreSQL schema reference |
| [`uml-artifacts/README.md`](uml-artifacts/README.md) | PlantUML architecture diagrams |

---

*MarketingMind AI — Recruiting operations surface*
