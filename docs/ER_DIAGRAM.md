# Entity relationship diagram

```mermaid
erDiagram
  ORGANIZATIONS ||--o{ TENANTS : contains
  ORGANIZATIONS ||--o{ MEMBERSHIPS : grants
  TENANTS ||--o{ MEMBERSHIPS : scopes
  USERS ||--o{ MEMBERSHIPS : has
  TENANTS ||--o{ BOARDS : owns
  BOARDS ||--o{ COLUMNS : contains
  TENANTS ||--o{ COLUMNS : scopes
  COLUMNS ||--o{ TASKS : contains
  BOARDS ||--o{ TASKS : contains
  TENANTS ||--o{ TASKS : scopes
  USERS ||--o{ TASKS : assigned
  TENANTS ||--o{ ACTIVITY_LOGS : records
  USERS ||--o{ ACTIVITY_LOGS : performs
  ORGANIZATIONS { string id PK string name }
  TENANTS { string id PK string organization_id FK string name }
  USERS { string id PK string name string email }
  MEMBERSHIPS { int id PK string user_id FK string organization_id FK string tenant_id FK string role }
  BOARDS { string id PK string tenant_id FK string name }
  COLUMNS { string id PK string tenant_id FK string board_id FK string name int position }
  TASKS { string id PK string tenant_id FK string board_id FK string column_id FK string title string description int position int version datetime updated_at }
  ACTIVITY_LOGS { int id PK string tenant_id FK string user_id FK string task_id string action string details datetime created_at }
```

Indexes prioritize tenant filtering and ordered task retrieval. In a production PostgreSQL schema, consider composite foreign keys to guarantee `(tenant_id, board_id)` and `(tenant_id, column_id)` consistency at the database layer, plus row-level security policies.
