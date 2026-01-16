"""
URL configuration for comparison app API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from comparison import views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'metrics', views.TaskMetricViewSet, basename='taskmetric')

urlpatterns = [
    # ViewSet URLs
    path('', include(router.urls)),

    # Summary endpoint
    path('summary/', views.comparison_summary, name='comparison-summary'),

    # Dashboard (HTML view)
    path('dashboard/', views.dashboard, name='dashboard'),

    # Dashboard API endpoints
    path('customers/', views.get_customers, name='get-customers'),
    path('generate/', views.generate_report, name='generate-report'),
    path('reports/<str:task_type>/', views.get_reports, name='get-reports'),
    path('clear/', views.clear_reports, name='clear-reports'),
]
