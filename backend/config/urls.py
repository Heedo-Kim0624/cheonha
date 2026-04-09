from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

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
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
