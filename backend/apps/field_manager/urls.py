from django.urls import path
from .views import (
    fm_login, fm_subscription_request, fm_return_request,
    fm_as_request, fm_blocked_dates, fm_request_history,
)

urlpatterns = [
    path('login/',                fm_login,                name='fm-login'),
    path('subscription-requests/', fm_subscription_request, name='fm-subscription-request'),
    path('return-requests/',       fm_return_request,       name='fm-return-request'),
    path('as-requests/',           fm_as_request,           name='fm-as-request'),
    path('blocked-dates/',         fm_blocked_dates,        name='fm-blocked-dates'),
    path('request-history/',       fm_request_history,      name='fm-request-history'),
]
