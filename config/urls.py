"""
URL configuration for Smart Meter Data Processor project.
"""

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Meters API
    path('api/', include('meters.urls')),

    # Comparison API (will create next)
    path('api/comparison/', include('comparison.urls')),

    # Django REST Framework browsable API auth
    path('api-auth/', include('rest_framework.urls')),
]
