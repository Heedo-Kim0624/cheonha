from django.urls import path

from apps.points import views as point_views

from . import views

app_name = "mobile"

urlpatterns = [
    path("app-config/", views.mobile_app_config, name="app-config"),
    path("register/", views.mobile_register, name="register"),
    path("login/", views.mobile_login, name="login"),
    path("signup/complete/", views.mobile_complete_signup, name="signup-complete"),
    path("refresh/", views.mobile_refresh, name="refresh"),
    path("password/", views.mobile_change_password, name="change-password"),
    path("vehicle-number/", views.mobile_update_vehicle_number, name="vehicle-number"),
    path("payroll-account/", views.mobile_update_payroll_account, name="payroll-account"),
    path(
        "vehicle-inspection-date/",
        views.mobile_update_vehicle_inspection_date,
        name="vehicle-inspection-date",
    ),
    path("status/", views.mobile_status, name="status"),
    path("profile/", views.mobile_profile, name="profile"),
    path(
        "work-session/start/",
        views.mobile_work_session_start,
        name="work-session-start",
    ),
    path(
        "work-session/heartbeat/",
        views.mobile_work_session_heartbeat,
        name="work-session-heartbeat",
    ),
    path(
        "work-session/checkpoint/",
        views.mobile_work_session_checkpoint,
        name="work-session-checkpoint",
    ),
    path(
        "work-session/stop/",
        views.mobile_work_session_stop,
        name="work-session-stop",
    ),
    path(
        "work-session/upload/",
        views.mobile_work_session_upload,
        name="work-session-upload",
    ),
    path("points/", point_views.mobile_points, name="points"),
    path("points/redeem/", point_views.mobile_redeem_points, name="points-redeem"),
    path("settlements/", views.mobile_settlements, name="settlements"),
    path(
        "settlement-inquiry/",
        views.mobile_settlement_inquiry,
        name="settlement-inquiry",
    ),
    path(
        "settlement-inquiry/comment/",
        views.mobile_settlement_inquiry_comment,
        name="settlement-inquiry-comment",
    ),
    path(
        "settlement-inquiry/read/",
        views.mobile_settlement_inquiry_read,
        name="settlement-inquiry-read",
    ),
    path("admin/approvals/", views.admin_mobile_approvals, name="admin-approvals"),
    path("admin/app-config/", views.admin_mobile_app_config, name="admin-app-config"),
    path(
        "admin/approvals/<int:pk>/",
        views.admin_mobile_approval_action,
        name="admin-approval-action",
    ),
    path("admin/users/", views.admin_mobile_users, name="admin-users"),
    path(
        "admin/users/<int:pk>/",
        views.admin_mobile_user_deactivate,
        name="admin-user-deactivate",
    ),
]
