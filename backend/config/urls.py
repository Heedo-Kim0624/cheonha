from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.views.static import serve

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # API Documentation
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # Auth Routes (frontend)
    path('api/v1/auth/', include('apps.accounts.auth_urls')),

    # API Routes
    path('api/v1/accounts/', include('apps.accounts.urls')),
    path('api/v1/dispatch/', include('apps.dispatch.urls')),
    path('api/v1/region/', include('apps.region.urls')),
    path('api/v1/settlement/', include('apps.settlement.urls')),
    path('api/v1/crew/', include('apps.crew.urls')),
    path('api/v1/partner/', include('apps.partner.urls')),
    path('api/v1/dashboard/', include('apps.dashboard.urls')),
    path('api/v1/one/', include('apps.one_settlement.urls')),

    # Mobile API (기사용 모바일 앱)
    path('api/v1/mobile/', include('apps.mobile.urls')),

    # 정산 문의
    path('api/v1/inquiry/', include('apps.inquiry.urls')),

    # 배송 추적 (BLE · GPS · Kalman 3-state 분석)
    path('api/v1/tracking/', include('apps.tracking.urls')),

    # 포인트 관리
    path('api/v1/points/', include('apps.points.urls')),

    # 인력 풀 (공유시트 연동)
    path('api/v1/manpower/', include('apps.manpower.urls')),

    # 권역 관리
    path('api/v1/territory/', include('apps.territory.urls')),

    # 차량 관리 (CLEVER 포털 - 차량관리 탭)
    path('api/v1/vehicle/', include('apps.vehicle_management.urls')),

    # 현장관리자 앱
    path('api/v1/field-manager/', include('apps.field_manager.urls')),
]

urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
