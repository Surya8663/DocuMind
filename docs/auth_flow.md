# Authentication & Tenant Isolation Flow

This sequence diagram illustrates the lifecycle of a request in DocuMind, highlighting how the JWT is validated, how the tenant ID is extracted into a thread-safe context variable, and how the ORM uses this to enforce Row-Level Security via the `TenantScopedManager`.

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant DRF_Throttle as DRF Rate Limiter
    participant Middleware as TenantMiddleware
    participant ContextVar as current_tenant_id
    participant API as API View
    participant Permission as IsTenantMember
    participant Manager as TenantScopedManager
    participant DB as PostgreSQL

    Note over Client, DB: Authentication (Login)
    Client->>DRF_Throttle: POST /api/auth/login/
    DRF_Throttle-->>Client: 429 Too Many Requests (if abused)
    DRF_Throttle->>API: Pass if below limit
    API->>DB: Validate Credentials
    DB-->>API: User & Tenant Data
    API-->>Client: 200 OK + JWT (claims: tenant_id, role)

    Note over Client, DB: Authenticated Request (e.g. /api/query/)
    Client->>Middleware: POST /api/query/ (Bearer JWT)
    Middleware->>Middleware: Verify JWT Signature & Expiry
    alt Invalid JWT
        Middleware-->>Client: 401 Unauthorized
    else Valid JWT
        Middleware->>Middleware: Extract tenant_id from JWT payload
        Middleware->>ContextVar: set(tenant_id)
        Middleware->>Permission: Forward Request
        
        Permission->>ContextVar: get()
        alt No tenant_id
            Permission-->>Client: 403 Forbidden
        else Has tenant_id
            Permission->>API: Execute View Logic
            API->>Manager: Query Models (e.g. DocumentChunk.objects.all())
            Manager->>ContextVar: get()
            Manager->>Manager: Append .filter(tenant_id=...)
            Manager->>DB: Execute scoped SQL Query
            DB-->>Manager: Filtered Results
            Manager-->>API: QuerySet
            API-->>Client: 200 OK (Isolated Data)
        end
        Middleware->>ContextVar: reset() (Cleanup)
    end
```
