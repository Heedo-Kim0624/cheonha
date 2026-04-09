from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SettlementViewSet, SettlementDetailViewSet

router = DefaultRouter()
router.register(r'settlements', SettlementViewSet, basename='settlement')
router.register(r'details', SettlementDetailViewSet, basename='settlement_detail')

urlpatterns = [
    path('', include(router.urls)),
]
