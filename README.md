# MarketingMind AI

Production-oriented recruiter operations workspace rebuilt from the legacy HTML prototypes.

## Modules

Command Center · Campaign Studio · Job Automation (resume AI, embeddings-based matching, supervised Quick Apply) · LinkedIn Recruiter · Day Report · Submissions · API Explorer · My Profile.

**Recent additions (v3.0):**

- **Supervised Quick Apply** — Playwright automation for **Dice, CareerBuilder, Monster, Indeed, ZipRecruiter, and LinkedIn**: fill profile/CV, pause for login/CAPTCHA, auto-submit, mark **Applied**.
- **Results tab status** — each job card shows **Applying → Applied** after Quick Apply (all supported portals).
- **Portal apply adapters** — `backend/app/services/portal_apply/` with demo/manual/supervised modes.
- **Expanded tests** — portal detection, registry, Playwright mock Easy Apply, API Quick Apply per portal (**138** automated tests).

**Also in v2.9:**

- **LinkedIn Recruiter** — save/bookmark recruiters, CSV bulk import, scheduled outreach, persistent templates.
- **Day Report** — nullable metrics as `-`, open-ended date filters, trend tooltips.
- **CV Analyzer** — manual Tailor resume after every analysis.
- **Campaign Studio** — divider, offline compose preview, animated send counter.

## Documentation

| Document | Description |
|----------|-------------|
| [`usermanual.md`](usermanual.md) | Full user manual (v3.0) — setup, modules, API, Quick Apply, notifications |
| [`usermanual.mfd`](usermanual.mfd) | Documentation manifest (JSON) |
| [`docs/DOCUMENTATION_INDEX.md`](docs/DOCUMENTATION_INDEX.md) | Index of all project docs |
| [`docs/TESTING_GUIDE.md`](docs/TESTING_GUIDE.md) | Automated test suites (138 tests) |
| [`backupfolder/FUNCTIONAL_TEST_CASES.md`](backupfolder/FUNCTIONAL_TEST_CASES.md) | Manual + automated functional tests |

## Configuration files

| File | Purpose |
|------|---------|
| [`backend/.env.example`](backend/.env.example) | Backend env template (DB, SMTP, SMS/Twilio, AI, Playwright Quick Apply) |
| [`frontend/.env.example`](frontend/.env.example) | Frontend env template (`VITE_API_BASE_URL`, `VITE_LOG_LEVEL`) |
| [`backend/pytest.ini`](backend/pytest.ini) | Pytest markers and options |
| [`backend/database/schema.sql`](backend/database/schema.sql) | PostgreSQL DDL (32 tables) |
| [`frontend/vite.config.js`](frontend/vite.config.js) | Vite dev server + vitest |

## Structure

- `frontend/`: React 19 + Vite application
- `backend/`: FastAPI + PostgreSQL (`pg_store`) with JSON seed fallback
- `backend/app/services/portal_apply/`: Multi-portal supervised apply (Playwright)
- `backupfolder/`: Legacy HTML prototypes and functional test cases

## Quick start

```bash
# Backend
cd backend
copy .env.example .env    # Windows
pip install -r requirements.txt
python -m playwright install chromium
python scripts/init_postgres_schema.py
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Frontend
cd frontend
copy .env.example .env
npm install
npm run dev
```

| Service | URL |
|---------|-----|
| Web app | http://localhost:5173 |
| API / Swagger | http://127.0.0.1:8000/docs |

> Port **8002** alternate: set `VITE_API_BASE_URL=http://127.0.0.1:8002` in `frontend/.env`.

## Supervised Quick Apply

```env
PORTAL_APPLY_MODE=supervised   # supervised | manual | demo
PORTAL_APPLY_AUTO_SUBMIT=true
PLAYWRIGHT_HEADLESS=false
PLAYWRIGHT_BROWSERS_PATH=.playwright-browsers
```

Supported boards: Dice · CareerBuilder · Monster · Indeed · ZipRecruiter · LinkedIn.

## Email & SMS notifications

Configure in `backend/.env`:

```env
# Shared SMTP (campaigns + transactional notifications)
SMTP_HOST=smtp.gmail.com
SMTP_USERNAME=your@email.com
SMTP_PASSWORD=app-password

# SMS (optional — demo mode when empty)
SMS_PROVIDER=twilio
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
```

Test from **My Profile → Notifications** or via `POST /api/notifications/test-email` and `test-sms`.

## Testing

```bash
# Backend (113 tests)
cd backend && .venv\Scripts\pip.exe install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q

# Frontend (25 tests)
cd frontend && npm test
```

## Demo accounts

| Role | Email | Password |
|------|-------|----------|
| User | `user@marketingmind.ai` | `User@123` |
| Admin | `admin@marketingmind.ai` | `Admin@123` |
| Super Admin | `superadmin@marketingmind.ai` | `Super@123` |

## PostgreSQL

```env
DATABASE_URL=postgresql+psycopg://postgres:admin@localhost:5432/postgres
USE_SEED_DATA=false
```

Schema only: `psql -f backend/database/schema.sql` · Schema + seed: `python scripts/init_postgres_schema.py`

## Troubleshooting

- **`uvicorn: command not found`:** Use `.venv\Scripts\python.exe -m uvicorn ...`
- **`Address already in use`:** Use `--port 8002` and update `VITE_API_BASE_URL`
- **Frontend network error:** Match `VITE_API_BASE_URL` to backend URL
- **Notifications in demo mode:** Set SMTP/Twilio credentials and set `*_FORCE_DEMO_MODE=false`
- **Quick Apply browser missing:** `playwright install chromium` and set `PLAYWRIGHT_BROWSERS_PATH`
