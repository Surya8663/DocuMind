from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


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
]
