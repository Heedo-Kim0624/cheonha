from django.urls import path

from . import views

app_name = "mobile"

urlpatterns = [
    # 기사용 모바일 API
    path("register/", views.mobile_register, name="register"),
    path("login/", views.mobile_login, name="login"),
    path("refresh/", views.mobile_refresh, name="refresh"),
    path("password/", views.mobile_change_password, name="change-password"),
    path("status/", views.mobile_status, name="status"),
    path("profile/", views.mobile_profile, name="profile"),
    path("settlements/", views.mobile_settlements, name="settlements"),
    # 관리자용 승인 API
    path("admin/approvals/", views.admin_mobile_approvals, name="admin-approvals"),
    path("admin/approvals/<int:pk>/", views.admin_mobile_approval_action, name="admin-approval-action"),
    path("admin/users/", views.admin_mobile_users, name="admin-users"),
    path("admin/users/<int:pk>/", views.admin_mobile_user_deactivate, name="admin-user-deactivate"),
]
