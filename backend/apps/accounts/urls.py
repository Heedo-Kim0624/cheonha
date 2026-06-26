from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CompanyAppPublicDetailView,
    CompanyAppSignupView,
    CompanyUserSignupRequestView,
    CompanyUserSignupView,
    CompanyAppViewSet,
    ShipperViewSet,
    UserViewSet,
    TeamViewSet,
    CustomTokenObtainPairView,
)

router = DefaultRouter()
router.register(r'company-apps', CompanyAppViewSet, basename='company-app')
router.register(r'shippers', ShipperViewSet, basename='shipper')
router.register(r'users', UserViewSet, basename='user')
router.register(r'teams', TeamViewSet, basename='team')

from .auth_views import SignupView

urlpatterns = [
    path('', include(router.urls)),
    path('company-app-signup/<str:token>/', CompanyAppSignupView.as_view(), name='company-app-signup'),
    path('company-app-public/<str:code>/', CompanyAppPublicDetailView.as_view(), name='company-app-public-detail'),
    path('company-user-signup/<str:code>/', CompanyUserSignupView.as_view(), name='company-user-signup'),
    path('company-user-signup-requests/', CompanyUserSignupRequestView.as_view(), name='company-user-signup-requests'),
    path(
        'company-user-signup-requests/<int:pk>/<str:action>/',
        CompanyUserSignupRequestView.as_view(),
        name='company-user-signup-request-action',
    ),
    path('signup/', SignupView.as_view(), name='signup'),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
