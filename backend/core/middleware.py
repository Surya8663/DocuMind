from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from .context import current_tenant_id


class TenantMiddleware:
    """
    Middleware that intercepts requests, authenticates the JWT early in the lifecycle,
    and extracts the tenant_id into a context variable for row-level security.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        jwt_auth = JWTAuthentication()
        # Reset token for each request to avoid cross-pollination in long-running threads
        token_to_reset = current_tenant_id.set(None)

        try:
            # We attempt to authenticate early in middleware so that any ORM calls
            # made within the view (even before the DRF permission class runs)
            # are scoped to the correct tenant.
            auth_tuple = jwt_auth.authenticate(request)
            if auth_tuple is not None:
                user, token = auth_tuple
                tenant_id = token.get("tenant_id")
                if tenant_id:
                    current_tenant_id.set(tenant_id)
        except (InvalidToken, TokenError):
            # We don't raise here; let DRF's view layer handle authentication denial
            pass

        response = self.get_response(request)

        # Cleanup
        current_tenant_id.reset(token_to_reset)

        return response
