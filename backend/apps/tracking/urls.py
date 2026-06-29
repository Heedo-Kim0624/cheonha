from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import TrackingSessionViewSet

router = DefaultRouter()
router.register(r'sessions', TrackingSessionViewSet, basename='tracking_session')

urlpatterns = [
    path("live-status/", views.live_work_statuses, name="tracking-live-status"),
    path("usage-overview/", views.tracking_usage_overview, name="tracking-usage-overview"),
    path("legal-consent-matrix/", views.legal_consent_matrix, name="tracking-legal-consent-matrix"),
    path('', include(router.urls)),
]
