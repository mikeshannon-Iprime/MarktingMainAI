# MarketingMind AI — Documentation Index

**Last updated:** 2026-07-21

Machine-readable manifest: [`usermanual.mfd`](../usermanual.mfd)

---

## Primary documentation

| Document | Audience | Description |
|----------|----------|-------------|
| [`usermanual.md`](../usermanual.md) | All users | Complete manual v3.0 — setup, RBAC, supervised Quick Apply, API, notifications |
| [`usermanual.mfd`](../usermanual.mfd) | Tools / CI | JSON manifest — docs, tests, config keys, service URLs |
| [`README.md`](../README.md) | Developers | Quick start and configuration file index |
| [`docs/QUICK_APPLY_DESIGN.md`](QUICK_APPLY_DESIGN.md) | Developers | Multi-portal Quick Apply architecture and UI design |

---

## Configuration

| File | Purpose |
|------|---------|
| [`backend/.env.example`](../backend/.env.example) | Database, SMTP, SMS/Twilio, AI keys, Playwright Quick Apply, feature flags |
| [`frontend/.env.example`](../frontend/.env.example) | `VITE_API_BASE_URL`, `VITE_LOG_LEVEL` |
| [`backend/pytest.ini`](../backend/pytest.ini) | Pytest paths and markers |
| [`frontend/vite.config.js`](../frontend/vite.config.js) | Vite + vitest |
| [`backend/database/schema.sql`](../backend/database/schema.sql) | PostgreSQL DDL (32 tables) |

---

## Testing & quality assurance

| Document | Audience | Description |
|----------|----------|-------------|
| [`docs/TESTING_GUIDE.md`](TESTING_GUIDE.md) | Developers / QA | 138 automated tests — pytest + vitest |
| [`backupfolder/FUNCTIONAL_TEST_CASES.md`](../backupfolder/FUNCTIONAL_TEST_CASES.md) | QA | Manual tests + automation mapping |

---

## Technical reference

| Document | Description |
|----------|-------------|
| [`backend/database/SCHEMA.md`](../backend/database/SCHEMA.md) | Table-level schema notes |
| [`backend/app/services/portal_apply/`](../backend/app/services/portal_apply/) | Job-board apply adapters (Dice, CareerBuilder, Monster, …) |
