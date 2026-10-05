# MarketingMind AI — Testing Guide

**Version:** 1.4  
**Last updated:** 2026-07-21

This guide covers the production-ready automated test suites that map to [`backupfolder/FUNCTIONAL_TEST_CASES.md`](../backupfolder/FUNCTIONAL_TEST_CASES.md).

---

## Quick run

```bash
# Backend (113 tests)
cd backend
.venv\Scripts\pip.exe install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q

# Frontend (25 tests)
cd frontend
npm install
npm test
```

**Expected result:** **138 tests** (113 backend + 25 frontend).

Portal Playwright mocks require Chromium under `backend/.playwright-browsers` (`playwright install chromium`). Functional API tests force `PORTAL_APPLY_MODE=demo` via `tests/conftest.py`.

---

## Backend (pytest)

### Layout

| File | Coverage |
|------|----------|
| `tests/conftest.py` | TestClient, demo login fixtures, `PORTAL_APPLY_MODE=demo` |
| `tests/test_functional_auth.py` | Login, invalid password, `/api/auth/me` |
| `tests/test_functional_job_automation.py` | Workspace, profile, search, Quick apply → Applied (Dice/CareerBuilder/Monster), multi-CV library |
| `tests/test_portal_apply.py` | Multi-portal detection, registry, demo/manual modes, Playwright Easy Apply mock → Applied (6 boards) |
| `tests/test_functional_campaigns.py` | Workspace, preview, drafts, contact import |
| `tests/test_functional_day_report.py` | Dashboard and filters |
| `tests/test_functional_submissions.py` | Submission MoM/YoY dashboard |
| `tests/test_functional_linkedin.py` | Discover, enrich, outreach generate |
| `tests/test_functional_notifications.py` | Email/SMS setup, preferences, delivery history |
| `tests/test_reporting_helpers.py` | MoM/YoY calculation helpers |
| `tests/test_portal_scraper.py` | Dice URL filters and live Next.js job-payload parsing |

### Configuration

- `backend/pytest.ini` — test paths, markers (`auth`, `job_automation`, `campaigns`, `notifications`, `playwright`, etc.)
- `backend/requirements-dev.txt` — `pytest`, `httpx`
- `backend/.env.example` — SMTP, Twilio, and Playwright Quick Apply vars

### Run by marker

```bash
cd backend
.venv\Scripts\python.exe -m pytest -m notifications -q
.venv\Scripts\python.exe -m pytest -m job_automation -q
.venv\Scripts\python.exe -m pytest -m playwright -q
.venv\Scripts\python.exe -m pytest tests/test_portal_apply.py -q
```

### Prerequisites

- Backend dependencies installed (`pip install -r requirements.txt`)
- Playwright Chromium for `@pytest.mark.playwright` cases
- PostgreSQL optional — tests use FastAPI `TestClient`; notification tests run in demo mode without Twilio/SMTP

### Demo credentials (fixtures)

| Role | Email | Password |
|------|-------|----------|
| user | `user@marketingmind.ai` | `User@123` |
| admin | `admin@marketingmind.ai` | `Admin@123` |
| super_admin | `superadmin@marketingmind.ai` | `Super@123` |

---

## Frontend (vitest)

### Layout

| File | Coverage |
|------|----------|
| `src/utils/validators.functional.test.js` | Form / payload validators |
| `src/utils/reportingHelpers.functional.test.js` | Day report / submission helpers |
| `src/utils/linkedinRecruiterHelpers.functional.test.js` | LinkedIn UI helpers |

```bash
cd frontend
npm test
```

---

## CI notes

- Keep `PORTAL_APPLY_MODE=demo` in CI for deterministic Quick Apply → Applied without headed browsers.
- Optionally run `pytest -m playwright` in a job that installs Chromium.
- Do not commit `.playwright/`, `.playwright-browsers/`, or `backend/test-results/`.
