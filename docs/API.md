# API Reference

All endpoints are prefixed with `/api`. For this demo, pass `X-User-Id` header. Defaults are demo convenience only.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/users` | List demo identities |
| GET | `/organizations` | Organizations visible to user |
| POST | `/organizations` | Create organization; caller becomes org admin |
| GET | `/tenants?organization_id=...` | List accessible branches |
| POST | `/tenants` | Org admin creates branch and starter board |
| GET | `/board?tenant_id=...` | Tenant-scoped board, columns, tasks |
| POST | `/boards?tenant_id=...` | Create board (tenant/org admin) |
| POST | `/columns?tenant_id=...&board_id=...` | Create column (tenant/org admin) |
| POST | `/tasks?tenant_id=...` | Create task |
| PATCH | `/tasks/{task_id}?tenant_id=...` | Update/move task, optional `expected_version` |
| DELETE | `/tasks/{task_id}?tenant_id=...` | Delete task |
| GET | `/activity?tenant_id=...` | Recent tenant activity |
| GET | `/docs` | OpenAPI interactive docs |

### Create task body
```json
{"title":"Prepare demo","description":"Acceptance criteria","column_id":"col-todo","position":0}
```

### Update or move task body
```json
{"title":"Prepare demo","description":"Acceptance criteria","column_id":"col-doing","position":0,"expected_version":1}
```
A stale `expected_version` returns HTTP 409 with the current task in the response detail. Resources outside the user's scope return 404.
