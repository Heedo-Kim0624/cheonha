from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CrewMemberViewSet, OvertimeSettingViewSet

router = DefaultRouter()
router.register(r'members', CrewMemberViewSet, basename='crew_member')
router.register(r'overtime', OvertimeSettingViewSet, basename='overtime_setting')

urlpatterns = [
    path('', include(router.urls)),
]
