from django.conf import settings
from django.db import OperationalError, ProgrammingError


VALID_COMPANY_APPS = ("cheonha", "abc")
DEFAULT_COMPANY_APP = "cheonha"


def is_clever_admin_user(user):
    names = set(getattr(settings, "CLEVER_ADMIN_USERNAMES", ["clever_admin"]))
    names.add("admin2")
    return bool(user and user.is_authenticated and getattr(user, "username", None) in names)


def is_known_company_app(value):
    if value in VALID_COMPANY_APPS:
        return True
    try:
        from apps.accounts.models import CompanyApp

        return CompanyApp.objects.filter(
            code=value,
            status=CompanyApp.Status.ACTIVE,
            deleted_at__isnull=True,
        ).exists()
    except (OperationalError, ProgrammingError):
        return value in VALID_COMPANY_APPS


def normalize_company_app(value):
    normalized = str(value or "").strip().lower()
    if is_known_company_app(normalized):
        return normalized
    return DEFAULT_COMPANY_APP


def get_company_app_from_request(request):
    requested = normalize_company_app(
        request.query_params.get("company_app")
        or request.headers.get("X-Company-App")
        or request.META.get("HTTP_X_COMPANY_APP")
    )
    user = getattr(request, "user", None)
    if user and user.is_authenticated and not is_clever_admin_user(user):
        team = getattr(user, "team", None)
        if team and getattr(team, "company_app", None):
            return normalize_company_app(team.company_app)
        if getattr(user, "company_app", None):
            return normalize_company_app(user.company_app)
    return requested


def filter_queryset_by_company_app(queryset, request, lookup="company_app"):
    company_app = get_company_app_from_request(request)
    return queryset.filter(**{lookup: company_app})
