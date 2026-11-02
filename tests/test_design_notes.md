# Manual acceptance checklist

- [ ] User in Hyderabad sees Hyderabad tasks and activity only.
- [ ] User without membership cannot read a tenant board or connect to its WebSocket.
- [ ] Task IDs from another tenant return 404 even if the ID is known.
- [ ] A column from another tenant cannot be used when creating/moving a task.
- [ ] Two clients in the same tenant receive task events.
- [ ] Two clients in different tenants do not receive each other's events.
- [ ] Stale `expected_version` returns 409.
- [ ] Moving a card updates its column and version.
- [ ] Reload after network recovery restores server state.
- [ ] Presence updates when clients connect/disconnect.
