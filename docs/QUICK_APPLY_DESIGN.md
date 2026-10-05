# Quick Apply — Design (v3.0)

**Last updated:** 2026-07-21

## Goal

One **Quick apply** control on Job Automation → **Results** that truly applies on the job board (not only opens a tab), then shows **Applied** on the same card for every supported portal.

## Supported portals

| Portal | Detection | Apply labels (examples) |
|--------|-----------|-------------------------|
| Dice | name / `dice.com` | Easy Apply, Apply Now |
| CareerBuilder | name / `careerbuilder.com` | Apply Now, Quick Apply |
| Monster | name / `monster.com` | Apply Now, 1-Click Apply |
| Indeed | name / `indeed.com` | Indeed Apply, Apply now |
| ZipRecruiter | name / `ziprecruiter.com` | Apply Now, 1-Click Apply |
| LinkedIn | name / `linkedin.com` | Easy Apply, Apply |

Unknown company career sites fall back to **manual** open + track.

## Architecture

```
Results card → POST /api/job-automation/apply { jobIds, supervised: true }
                    │
                    ├─ resolve_adapter(portal, url)
                    │     JobBoardApplyAdapter  OR  ManualApplyAdapter
                    │
                    ├─ Background thread → child process (Playwright, Windows-safe)
                    │     fill fields → upload CV → auto-submit → confirmation
                    │
                    └─ GET /applications/{id} polled by UI
                          attemptStatus → Results badge + button label
```

### Backend package

`backend/app/services/portal_apply/`

| Module | Role |
|--------|------|
| `portals.py` | Portal specs, detection, labels |
| `job_board.py` | Shared Playwright supervised apply (`DiceApplyAdapter` alias) |
| `manual.py` | Open URL + track |
| `registry.py` | Adapter resolution |
| `base.py` | Payload / result types |

### Modes (`PORTAL_APPLY_MODE`)

| Mode | Behavior |
|------|----------|
| `supervised` | Headed Chromium; login/CAPTCHA pause; auto-submit optional |
| `manual` | System browser + tracker |
| `demo` | Immediate Applied (tests/CI) |

## Results UI design

| State | Badge | Button |
|-------|-------|--------|
| Idle | (none) | **Quick apply** |
| In progress | Applying | **Applying…** (disabled) |
| Success | Applied | **Applied** (disabled, checkmark) |
| Needs attention | Action Needed | Quick apply available again after fail |

Status is keyed by `jobResultId` so Dice, CareerBuilder, Monster, and other boards all update the same way after submit.

## Data

- `UserResume.file_bytes` — CV upload for form attach
- `JobApplication.attempt_status`, `attempt_detail`, `confirmation_url`
- API: `POST /apply`, `GET /applications/{id}`, `GET /applications`

## Tests

- `tests/test_portal_apply.py` — detection, registry, demo, Playwright mock Easy Apply for all 6 boards
- `tests/test_functional_job_automation.py` — API Quick Apply → Applied per Dice / CareerBuilder / Monster
