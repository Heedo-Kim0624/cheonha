from django.urls import path
from . import auth_views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(), name='auth_login'),
    path('refresh/', auth_views.RefreshTokenView.as_view(), name='auth_refresh'),
    path('profile/', auth_views.ProfileView.as_view(), name='auth_profile'),
    path('logout/', auth_views.LogoutView.as_view(), name='auth_logout'),
    path('signup/', auth_views.SignupView.as_view(), name='auth_signup'),
]
