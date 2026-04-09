from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RegionViewSet, RegionPriceViewSet, PriceHistoryViewSet

router = DefaultRouter()
router.register(r'regions', RegionViewSet, basename='region')
router.register(r'prices', RegionPriceViewSet, basename='region_price')
router.register(r'price-history', PriceHistoryViewSet, basename='price_history')

urlpatterns = [
    path('', include(router.urls)),
]
