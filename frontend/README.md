# MarketingMind AI — Frontend

React 19 + Vite 8 application for the MarketingMind recruiter console.

## Configuration

Copy `frontend/.env.example` → `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_LOG_LEVEL=debug
```

| Variable | Purpose |
|----------|---------|
| `VITE_API_BASE_URL` | Backend API base URL (must match running uvicorn port) |
| `VITE_LOG_LEVEL` | Client log level: `debug`, `info`, `warn`, `error` |

If backend runs on port **8002**, set `VITE_API_BASE_URL=http://127.0.0.1:8002`.

## Commands

```bash
npm install
npm run dev          # http://localhost:5173
npm run build        # production build → dist/
npm test             # vitest (21 tests)
npm run lint
```

## Key paths

| Path | Purpose |
|------|---------|
| `src/api/client.js` | Axios API client (auth, campaigns, notifications, …) |
| `src/pages/UserProfilePage.jsx` | Profile, settings, **notifications** (email/SMS test) |
| `src/pages/CampaignStudioPage.jsx` | Campaign SMTP settings |
| `src/utils/logger.js` | Production client logging |
| `vite.config.js` | Dev server proxy + vitest config |

## Notification UI

**My Profile → Notifications:** email/SMS toggles, test send buttons, delivery history.

Requires backend notification APIs (`/api/notifications/*`) — see `usermanual.md` §23.
