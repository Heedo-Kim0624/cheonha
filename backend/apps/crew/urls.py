from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CrewMemberViewSet, OvertimeSettingViewSet, YongchaPayGroupViewSet

router = DefaultRouter()
router.register(r'members', CrewMemberViewSet, basename='crew_member')
router.register(r'overtime', OvertimeSettingViewSet, basename='overtime_setting')
router.register(r'yongcha-pay-groups', YongchaPayGroupViewSet, basename='yongcha_pay_group')

urlpatterns = [
    path('', include(router.urls)),
]
