import contextvars

# Context variable to hold the current tenant ID safely across asynchronous or threaded execution
current_tenant_id = contextvars.ContextVar("current_tenant_id", default=None)
