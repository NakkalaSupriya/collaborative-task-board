# Collaborative Task Board (Multi-Tenant Starter)

A runnable starter implementation for a real-time Kanban task board with organization → tenant/branch → board hierarchy.

## Stack
- Python 3.11+
- FastAPI + SQLite
- WebSockets for tenant-scoped live updates
- Vanilla HTML/CSS/JavaScript frontend with drag-and-drop
- SQL schema and Mermaid ER diagram

## Run on Windows
```bat
cd collaborative_task_board
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000

If `py` is unavailable, use `python` instead.

## Demo identities and roles
The demo login selector uses seeded identities:
- `u-org-admin`: organization admin
- `u-tenant-admin`: tenant admin
- `u-member`: member

Choose an organization and branch, then create/move tasks. Open the app in another browser tab and choose the same tenant to see WebSocket updates. This is a learning/demo authentication mechanism, **not production authentication**.

## Architecture
- `app/main.py`: API routes, demo auth, WebSocket endpoint, event broadcasting.
- `app/database.py`: SQLite connection and schema initialization.
- `app/seed.py`: sample organization, tenants, users, memberships, board, columns, tasks.
- `app/static/`: frontend.
- `docs/`: API notes, WebSocket protocol, ER diagram.

## Tenancy and security model
Every board, column, and task carries `tenant_id`. Reads and writes derive tenant scope from the selected tenant plus membership checks; task IDs alone are never treated as authorization. A task's tenant must match its column's tenant and board's tenant. Organization admins can access tenants in their organization; tenant admins and members must have a membership in that tenant. The app returns `404` for out-of-scope resources to avoid confirming their existence.

The demo identity is passed in `X-User-Id`; replace it with signed sessions/OIDC/JWT and never trust a client-supplied identity in production. For stronger isolation, use PostgreSQL with row-level security and tenant-aware indexes.

## Concurrency strategy
Tasks have an integer `version`. Updates and moves may include `expected_version`; if the stored version differs, the API returns `409 Conflict` with the current task. The frontend refreshes after conflicts. Ordering uses `position`; moves reassign position and increment the version. For high contention, use a transaction plus unique ordering strategy (e.g. fractional indexing) and retry policy.

## Advanced requirements / trade-offs
- WebSocket broadcasts are scoped by tenant ID and sent only to connected authorized members.
- Presence is a lightweight in-memory list of connected demo users per tenant. It resets on server restart and is not distributed across multiple workers.
- Optimistic UI: drag/drop updates the DOM immediately; API errors trigger a refresh.
- Undo: task updates include a simple "Undo last move" action in the frontend. It is best-effort and can conflict if another user has changed the task.
- Activity logs are tenant-scoped and recorded for task create/update/move/delete.
- SQLite is appropriate for local evaluation, not high-write production use. Use PostgreSQL and a shared pub/sub layer (Redis) for multiple app instances.
- This starter intentionally keeps UI and API in one FastAPI service for easy setup.

## API docs
Interactive OpenAPI docs: http://127.0.0.1:8000/docs
See `docs/API.md` and `docs/WEBSOCKETS.md`.

## Important
This is an educational starter, not a hardened production system. Add real authentication, rate limits, audit retention, CSRF protections if cookie auth is used, input validation, automated security tests, and deployment secrets before production.
