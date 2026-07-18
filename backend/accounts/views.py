from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView

from core.permissions import IsTenantMember

from .models import DocumentChunk
from .serializers import CustomTokenObtainPairSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Login endpoint that issues our custom JWT containing tenant_id and role.
    Rate limited by DRF default AnonRateThrottle to prevent credential stuffing.
    """

    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [AnonRateThrottle]


@api_view(["POST"])
@permission_classes([IsTenantMember])
def query_view_stub(request):
    """
    A stub endpoint meant to simulate the actual AI querying process.
    We use this primarily in the security test suite to prove that
    the TenantScopedManager successfully filters out cross-tenant data leaks.
    """
    # The malicious user might try to pass a tenant_id in the body, but
    # the TenantScopedManager strictly uses the contextvar derived from their JWT.

    # Just attempting to query chunks (which will automatically be filtered)
    chunk_count = DocumentChunk.objects.count()

    return Response(
        {"message": "Query processed", "accessible_chunks_in_db": chunk_count}
    )
