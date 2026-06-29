from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DashboardViewSet, WorkflowMonitorViewSet

router = DefaultRouter()
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'workflow-monitor', WorkflowMonitorViewSet, basename='workflow-monitor')

urlpatterns = [
    path('', include(router.urls)),
]
