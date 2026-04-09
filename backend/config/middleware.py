from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


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
