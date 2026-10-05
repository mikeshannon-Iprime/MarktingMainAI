# UML Artifacts

PlantUML diagrams for the MarketingMind AI frontend and backend.

## Diagram Inventory

- `frontend-component.puml` — Frontend component architecture
- `frontend-sequence.puml` — Frontend-to-backend runtime sequence
- `backend-component.puml` — Backend layered component architecture
- `backend-sequence.puml` — Backend request processing sequences
- `system-deployment.puml` — End-to-end deployment/runtime topology

## Render

```bash
cd uml-artifacts
plantuml *.puml
```

## Scope notes

- Diagrams reflect routes, services, and data flow in the current codebase.
- PostgreSQL is the primary persistence layer (`pg_store`); JSON seed is fallback.
- Notification services (`notification_service`, `sms_client`, `campaign_email`) may not appear in older diagrams — regenerate after major changes.

## Related configuration

| Resource | Path |
|----------|------|
| API routes | `backend/app/api/routes.py` |
| DB models (30 tables) | `backend/app/db/models.py` |
| Env template | `backend/.env.example` |
