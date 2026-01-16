"""
URL configuration for meters app API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from meters import views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'customers', views.CustomerViewSet, basename='customer')
router.register(r'meters', views.SmartMeterViewSet, basename='smartmeter')
router.register(r'readings', views.MeterReadingViewSet, basename='meterreading')
router.register(r'aggregates', views.UsageAggregateViewSet, basename='usageaggregate')

urlpatterns = [
    # ViewSet URLs
    path('', include(router.urls)),

    # Task trigger endpoint
    path('tasks/trigger/', views.trigger_task, name='trigger-task'),
]
