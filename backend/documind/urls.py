from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import CustomTokenObtainPairView, query_view_stub


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """Standard health check endpoint that reports service status."""
    return JsonResponse(
        {
            "status": "healthy",
            "service": "DocuMind API Backend",
            "version": "0.1.0",
        }
    )


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health_check"),
    path(
        "api/auth/login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"
    ),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/query/", query_view_stub, name="query_stub"),
]
