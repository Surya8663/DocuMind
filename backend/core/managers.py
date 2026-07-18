from django.db import models

from .context import current_tenant_id


class TenantScopedManager(models.Manager):
    """
    A custom manager that enforces row-level tenant isolation.

    It intercepts all queryset creations and appends a `.filter(tenant_id=...)`
    if a tenant is active in the current request context. This makes it impossible
    for developers to accidentally leak cross-tenant data by forgetting a `.filter()`
    call in a view, neutralizing IDOR vulnerabilities at the ORM layer.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        tenant_id = current_tenant_id.get()
        if tenant_id:
            # We strictly enforce the filter if tenant_id is populated.
            return qs.filter(tenant_id=tenant_id)
        # If no tenant is in context (e.g., celery tasks, management commands
        # that haven't explicitly set the context), we return the unfiltered qs.
        # In a strict environment, you might raise an exception here if a tenant
        # context is absolutely required for all operations.
        return qs
