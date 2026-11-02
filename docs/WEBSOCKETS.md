# WebSocket protocol

Connect to `ws://127.0.0.1:8000/ws/{tenant_id}?user_id={demo_user_id}`.

- Connection is authorized against the tenant membership before acceptance.
- Connections are held in an in-memory room keyed by `tenant_id`.
- Presence message: `{"type":"presence","users":["u-member"]}`
- Task create event: `{"type":"task_created","task":{...}}`
- Task update/move event: `{"type":"task_updated","task":{...}}`
- Task delete event: `{"type":"task_deleted","task_id":"..."}`
- Clients send text heartbeats; reconnect with backoff after disconnect.

Production note: in-memory rooms work only for one process. For multiple workers, use Redis Pub/Sub or another broker, authenticate with secure tokens, validate origin, and add message size/rate limits.
