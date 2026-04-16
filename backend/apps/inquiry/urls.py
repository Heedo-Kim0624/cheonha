from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SettlementInquiryViewSet

router = DefaultRouter()
router.register(r'inquiries', SettlementInquiryViewSet, basename='inquiry')

urlpatterns = [
    path('', include(router.urls)),
]
