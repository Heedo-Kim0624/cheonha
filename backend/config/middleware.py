from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.db import connection
import logging

logger = logging.getLogger(__name__)


class TenantSchemaRoutingMiddleware:
    """Optional tenant schema router.

    Default settings keep this fully inactive. When enabled later, a request is
    routed only if the global flag, the allow-list, and the CompanyTenant row all
    agree. The search_path is always restored before the connection is reused.
    """

    CENTRAL_PATH_PREFIXES = (
        "/admin/",
        "/api/v1/schema/",
        "/api/v1/docs/",
        "/api/v1/accounts/company-apps/",
        "/api/v1/accounts/company-signup/",
        "/api/v1/accounts/company-admin/",
        "/api/v1/accounts/shippers/",
        "/api/v1/auth/clever-login/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        routed = False
        try:
            routed = self._maybe_route_to_tenant(request)
            response = self.get_response(request)
            return response
        finally:
            if routed:
                self._restore_public_search_path()

    def _maybe_route_to_tenant(self, request):
        if not getattr(settings, "TENANT_SCHEMA_ROUTING_ENABLED", False):
            return False
        if connection.vendor != "postgresql":
            return False
        if self._is_central_path(request.path):
            return False

        company_code = self._company_code_from_request(request)
        if not company_code:
            return False

        allowed_companies = set(getattr(settings, "TENANT_SCHEMA_COMPANIES", []))
        if company_code not in allowed_companies:
            return False

        tenant = self._tenant_for_company(company_code)
        if not tenant:
            return False

        schema_name = tenant.schema_name
        quoted_schema = connection.ops.quote_name(schema_name)
        with connection.cursor() as cursor:
            cursor.execute(f"SET search_path TO {quoted_schema}, public")
        request.tenant_schema_name = schema_name
        request.tenant_company_app = company_code
        logger.info("Tenant schema routing enabled for company=%s schema=%s", company_code, schema_name)
        return True

    def _is_central_path(self, path):
        return any(path.startswith(prefix) for prefix in self.CENTRAL_PATH_PREFIXES)

    def _company_code_from_request(self, request):
        value = (
            request.GET.get("company_app")
            or request.headers.get("X-Company-App")
            or request.META.get("HTTP_X_COMPANY_APP")
        )
        return str(value or "").strip().lower()

    def _tenant_for_company(self, company_code):
        try:
            from apps.accounts.models import CompanyTenant

            return (
                CompanyTenant.objects.select_related("company_app")
                .filter(
                    company_app__code=company_code,
                    company_app__status="ACTIVE",
                    company_app__deleted_at__isnull=True,
                    status__in=("READY", "ACTIVE"),
                    routing_enabled=True,
                )
                .first()
            )
        except Exception:
            logger.exception("Tenant schema lookup failed for company=%s", company_code)
            return None

    def _restore_public_search_path(self):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO public")
        except Exception:
            logger.exception("Failed to restore PostgreSQL search_path to public")


class FeatureFlagMiddleware(MiddlewareMixin):
    """
    Feature flag 검증 미들웨어
    각 앱별로 feature flag를 확인하고 비활성화된 경우 503 반환
    """

    FEATURE_FLAG_PATHS = {
        '/api/v1/accounts/': 'accounts',
        '/api/v1/dispatch/': 'dispatch',
        '/api/v1/region/': 'region',
        '/api/v1/settlement/': 'settlement',
        '/api/v1/crew/': 'crew',
        '/api/v1/partner/': 'partner',
        '/api/v1/dashboard/': 'dashboard',
        '/api/v1/one/': 'one',
    }

    def process_request(self, request):
        # Feature flag 검증
        for path_prefix, flag_name in self.FEATURE_FLAG_PATHS.items():
            if request.path.startswith(path_prefix):
                if not settings.FEATURE_FLAGS.get(flag_name, False):
                    logger.warning(f'Feature flag "{flag_name}" is disabled. Path: {request.path}')
                    return JsonResponse(
                        {'error': f'서비스 "{flag_name}"은(는) 현재 사용할 수 없습니다.'},
                        status=503
                    )
                break
        return None
