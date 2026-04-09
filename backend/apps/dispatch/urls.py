from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DispatchUploadViewSet, DispatchRecordViewSet

router = DefaultRouter()
router.register(r'uploads', DispatchUploadViewSet, basename='dispatch_upload')
router.register(r'records', DispatchRecordViewSet, basename='dispatch_record')

urlpatterns = [
    path('', include(router.urls)),
]
