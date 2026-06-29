from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import OneDriverViewSet, OneStatementViewSet, OneSummaryViewSet, OneUploadViewSet

router = DefaultRouter()
router.register(r"uploads", OneUploadViewSet, basename="one-upload")
router.register(r"summary", OneSummaryViewSet, basename="one-summary")
router.register(r"drivers", OneDriverViewSet, basename="one-driver")
router.register(r"statements", OneStatementViewSet, basename="one-statement")

urlpatterns = [
    path("", include(router.urls)),
]

