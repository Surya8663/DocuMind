from rest_framework import permissions

from .context import current_tenant_id


class IsTenantMember(permissions.BasePermission):
    """
    Allows access only to authenticated users who belong to a valid tenant.
    """

    message = "You must belong to a tenant to access this resource."

    def has_permission(self, request, view):
        # The user must be authenticated
        if not bool(request.user and request.user.is_authenticated):
            return False

        # For our multi-tenant architecture, the tenant must be resolved in context
        # (either by JWT payload interception or normal DRF auth)
        return bool(current_tenant_id.get())
