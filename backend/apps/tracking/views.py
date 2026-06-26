import codecs
import re
from urllib.parse import quote

from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from apps.crew.models import CrewMember
from apps.common.company_scope import get_company_app_from_request
from apps.mobile.models import LEGAL_DOCUMENT_VERSION, LegalConsentHistory

from .models import TrackingSession, CameraCapture, BleLog, Cycle, LocationPoint
from .serializers import (
    SessionListSerializer,
    SessionDetailSerializer,
    LocationPointSerializer,
    BleLogSerializer,
    CameraCaptureSerializer,
    CycleSerializer,
)
from .services import build_tracking_session_csv, raw_tracking_csv_path


def _download_filename(session):
    crew_name = session.crew_member.name if session.crew_member else "crew"
    vehicle_number = session.crew_member.vehicle_number if session.crew_member else ""
    base = "_".join(
        part for part in [
            "work_session",
            crew_name,
            vehicle_number,
            session.session_date.isoformat(),
            str(session.id),
        ] if part
    )
    return re.sub(r'[\\/:*?"<>|\s]+', "_", base).strip("_") + ".csv"


def _is_admin_user(user):
    return bool(
        user
        and user.is_authenticated
        and (user.is_staff or getattr(user, "is_admin", lambda: False)())
    )


def _admin_required(request):
    if _is_admin_user(request.user):
        return None
    return Response(
        {"detail": "관리자 권한이 필요합니다."},
        status=status.HTTP_403_FORBIDDEN,
    )


def _get_optional_related(instance, attr_name):
    try:
        return getattr(instance, attr_name)
    except Exception:
        return None


APP_REQUIRED_LEGAL_ITEMS = [
    {
        "key": "app_terms",
        "label": "배송원 이용약관",
        "agreement_key": "agree_terms",
        "document_key": "app_terms",
        "agreed_field": "terms_agreed_at",
    },
    {
        "key": "privacy_policy",
        "label": "개인정보처리방침",
        "agreement_key": "agree_privacy_policy",
        "document_key": "privacy_policy",
        "agreed_field": "privacy_policy_agreed_at",
    },
    {
        "key": "location_terms",
        "label": "위치기반서비스 이용약관",
        "agreement_key": "agree_location_terms",
        "document_key": "location_terms",
        "agreed_field": "location_terms_agreed_at",
    },
    {
        "key": "data_processing",
        "label": "제3자 정보제공 동의",
        "agreement_key": "agree_data_processing",
        "document_key": "data_processing",
        "agreed_field": "third_party_information_agreed_at",
    },
]


class TrackingSessionViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'delete', 'head', 'options']

    """
    배송 추적 세션 API
    - GET /sessions/?date=YYYY-MM-DD&team=<team_id>
    - GET /sessions/{id}/            (상세: points + captures + cycles)
    - GET /sessions/{id}/points/     (경량 GPS 배열)
    - GET /sessions/{id}/ble/        (BLE 로그)
    - GET /sessions/{id}/captures/   (촬영 이벤트)
    - GET /sessions/{id}/cycles/     (분석된 사이클)
    - GET /sessions/available_dates/?team=<id> (날짜 피커용)
    """
    permission_classes = [permissions.IsAuthenticated]

    def _detail_queryset(self):
        return TrackingSession.objects.select_related(
            'crew_member', 'crew_member__team'
        )

    def _apply_user_scope(self, qs):
        user = self.request.user
        if user.is_staff or getattr(user, 'is_admin', lambda: False)():
            return qs.filter(crew_member__team__company_app=get_company_app_from_request(self.request))
        if getattr(user, 'team_id', None):
            return qs.filter(crew_member__team_id=user.team_id)
        return qs.none()

    def _get_session_object(self, *, prefetch_detail=False):
        qs = self._apply_user_scope(self._detail_queryset())
        if prefetch_detail:
            qs = qs.prefetch_related(
                Prefetch(
                    'points',
                    queryset=LocationPoint.objects.only(
                        'session_id', 'recorded_at', 'lat', 'lon',
                        'accuracy_m', 'speed_kmh', 'state', 'cycle_id',
                    ).order_by('recorded_at'),
                ),
                Prefetch(
                    'captures',
                    queryset=CameraCapture.objects.only(
                        'session_id', 'started_at', 'captured_at',
                        'duration_ms', 'device', 'lat', 'lon', 'cycle_id',
                    ).order_by('captured_at'),
                ),
                Prefetch(
                    'cycles',
                    queryset=Cycle.objects.only(
                        'session_id', 'cycle_no', 'started_at', 'ended_at',
                        'sr_seconds', 'dl_seconds', 'distance_m',
                        'avg_speed_kmh', 'avg_accuracy_m', 'capture_count',
                    ).order_by('cycle_no'),
                ),
            )
        return get_object_or_404(qs, pk=self.kwargs.get('pk'))

    def get_queryset(self):
        qs = TrackingSession.objects.select_related(
            'crew_member', 'crew_member__team'
        ).annotate(
            capture_count=Count('captures', distinct=True),
            has_rssi_count=Count('ble_logs', filter=Q(ble_logs__rssi__isnull=False), distinct=True),
        ).order_by('-session_date', '-started_at', '-created_at', 'crew_member__code')

        date = self.request.query_params.get('date')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        team = self.request.query_params.get('team')
        crew = self.request.query_params.get('crew')

        if date:
            qs = qs.filter(session_date=date)
        if start_date:
            qs = qs.filter(session_date__gte=start_date)
        if end_date:
            qs = qs.filter(session_date__lte=end_date)
        if team:
            qs = qs.filter(crew_member__team_id=team)
        if crew:
            qs = qs.filter(crew_member_id=crew)

        # 권한: 관리자는 전체, 팀장은 자기 팀만
        user = self.request.user
        if not (user.is_staff or getattr(user, 'is_admin', lambda: False)()):
            if getattr(user, 'team_id', None):
                qs = qs.filter(crew_member__team_id=user.team_id)
            else:
                qs = qs.none()

        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SessionDetailSerializer
        return SessionListSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self._get_session_object(prefetch_detail=True)
        # 상세는 무거우니까 prefetch
        serializer = SessionDetailSerializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def points(self, request, pk=None):
        session = self._get_session_object()
        qs = session.points.all().only('recorded_at', 'lat', 'lon', 'accuracy_m', 'speed_kmh', 'state', 'cycle_id')
        return Response(LocationPointSerializer(qs, many=True).data)

    @action(detail=True, methods=['get'])
    def ble(self, request, pk=None):
        session = self._get_session_object()
        return Response(BleLogSerializer(session.ble_logs.all(), many=True).data)

    @action(detail=True, methods=['get'])
    def captures(self, request, pk=None):
        session = self._get_session_object()
        return Response(CameraCaptureSerializer(session.captures.all(), many=True).data)

    @action(detail=True, methods=['get'])
    def cycles(self, request, pk=None):
        session = self._get_session_object()
        return Response(CycleSerializer(session.cycles.all(), many=True).data)

    @action(detail=True, methods=['get'], url_path='download_csv')
    def download_csv(self, request, pk=None):
        """
        Download the uploaded mobile work-session CSV.

        If the raw file is unavailable for older sessions, a CSV is regenerated
        from stored tracking rows. Regenerated CSV cannot include barometer
        values because they were not persisted previously.
        """
        session = self._get_session_object()
        raw_path = raw_tracking_csv_path(session.id)
        source = 'generated'

        if default_storage.exists(raw_path):
            with default_storage.open(raw_path, 'rb') as fp:
                content = fp.read()
            source = 'raw'
            if not content.startswith(codecs.BOM_UTF8):
                content = codecs.BOM_UTF8 + content
        else:
            content = build_tracking_session_csv(session).encode('utf-8-sig')

        filename = _download_filename(session)
        response = HttpResponse(content, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = (
            f"attachment; filename*=UTF-8''{quote(filename)}"
        )
        response['X-Cheonha-Csv-Source'] = source
        return response

    @action(detail=False, methods=['get'], url_path='available_dates')
    def available_dates(self, request):
        qs = self.get_queryset().values_list('session_date', flat=True).distinct().order_by('-session_date')
        return Response([d.isoformat() for d in qs])

    @action(detail=False, methods=['delete'], url_path='bulk_delete')
    def bulk_delete(self, request):
        """
        DELETE /tracking/sessions/bulk_delete/?team=<id>&date=YYYY-MM-DD
        해당 조건의 세션을 일괄 삭제.
        """
        qs = self.get_queryset()
        date = request.query_params.get('date')
        team = request.query_params.get('team')
        if not (date or team):
            return Response(
                {'detail': 'team 또는 date 중 최소 하나는 필수입니다.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # get_queryset 은 이미 team/date 필터링 지원하지만, 안전하게 다시 적용
        if date:
            qs = qs.filter(session_date=date)
        if team:
            qs = qs.filter(crew_member__team_id=team)
        count = qs.count()
        qs.delete()
        return Response({'deleted': count}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def live_work_statuses(request):
    forbidden = _admin_required(request)
    if forbidden:
        return forbidden

    team = request.query_params.get("team")
    queryset = CrewMember.objects.filter(
        is_active=True,
        is_yongcha=False,
        team__company_app=get_company_app_from_request(request),
    ).select_related(
        "team",
        "mobile_app_user",
        "live_work_status",
    )
    if team:
        queryset = queryset.filter(team_id=team)

    rows = []
    working_count = 0
    permission_ok_count = 0
    for crew in queryset.order_by("team__code", "name", "code"):
        live_status = _get_optional_related(crew, "live_work_status")
        mobile_user = _get_optional_related(crew, "mobile_app_user")
        is_working = bool(
            live_status and live_status.status == live_status.Status.RUNNING
        )
        if is_working:
            working_count += 1
        if live_status and live_status.background_location_granted:
            permission_ok_count += 1

        rows.append(
            {
                "id": crew.id,
                "name": crew.name,
                "code": crew.code,
                "team_id": crew.team_id,
                "team_code": crew.team.code if crew.team else "",
                "team_name": crew.team.name if crew.team else "",
                "vehicle_number": (
                    live_status.current_vehicle_number
                    if live_status and live_status.current_vehicle_number
                    else (crew.vehicle_number or "")
                ),
                "has_mobile_account": bool(mobile_user),
                "app_version": (
                    (live_status.last_app_version if live_status else "")
                    or (mobile_user.last_app_version if mobile_user else "")
                    or ""
                ),
                "last_login_at": (
                    mobile_user.last_login_at.isoformat()
                    if mobile_user and mobile_user.last_login_at
                    else None
                ),
                "is_working": is_working,
                "status": live_status.status if live_status else "STOPPED",
                "session_started_at": (
                    live_status.session_started_at.isoformat()
                    if live_status and live_status.session_started_at
                    else None
                ),
                "session_ended_at": (
                    live_status.session_ended_at.isoformat()
                    if live_status and live_status.session_ended_at
                    else None
                ),
                "last_seen_at": (
                    live_status.last_seen_at.isoformat()
                    if live_status and live_status.last_seen_at
                    else None
                ),
                "background_location_granted": bool(
                    live_status and live_status.background_location_granted
                ),
            }
        )

    return Response(
        {
            "summary": {
                "crew_count": len(rows),
                "working_count": working_count,
                "background_location_ok_count": permission_ok_count,
            },
            "rows": rows,
        }
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def tracking_usage_overview(request):
    forbidden = _admin_required(request)
    if forbidden:
        return forbidden

    team = request.query_params.get("team")
    date = request.query_params.get("date")
    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")

    crew_queryset = CrewMember.objects.filter(
        is_active=True,
        is_yongcha=False,
        team__company_app=get_company_app_from_request(request),
    ).select_related(
        "team",
        "mobile_app_user",
        "live_work_status",
    )
    session_queryset = TrackingSession.objects.select_related(
        "crew_member",
        "crew_member__team",
    ).filter(
        crew_member__is_yongcha=False,
        crew_member__team__company_app=get_company_app_from_request(request),
    ).only(
        "id",
        "crew_member_id",
        "session_date",
        "started_at",
        "ended_at",
        "created_at",
        "app_version",
        "total_seconds",
        "iv_seconds",
        "sr_seconds",
        "dl_seconds",
        "distance_m",
        "cycle_count",
        "bbox_min_lat",
        "bbox_min_lon",
        "bbox_max_lat",
        "bbox_max_lon",
        "crew_member__name",
        "crew_member__code",
        "crew_member__vehicle_number",
        "crew_member__team_id",
        "crew_member__team__name",
    )

    if team:
        crew_queryset = crew_queryset.filter(team_id=team)
        session_queryset = session_queryset.filter(crew_member__team_id=team)
    if date:
        session_queryset = session_queryset.filter(session_date=date)
    if start_date:
        session_queryset = session_queryset.filter(session_date__gte=start_date)
    if end_date:
        session_queryset = session_queryset.filter(session_date__lte=end_date)

    sessions = list(session_queryset)
    session_ids = [session.id for session in sessions]
    capture_count_map = {}
    has_rssi_ids = set()
    if session_ids:
        capture_count_map = dict(
            CameraCapture.objects.filter(session_id__in=session_ids)
            .values("session_id")
            .annotate(count=Count("id"))
            .values_list("session_id", "count")
        )
        has_rssi_ids = set(
            BleLog.objects.filter(
                session_id__in=session_ids,
                rssi__isnull=False,
            )
            .values_list("session_id", flat=True)
            .distinct()
        )

    for session in sessions:
        session.capture_count = int(capture_count_map.get(session.id, 0) or 0)
        session.has_rssi_count = 1 if session.id in has_rssi_ids else 0

    sessions.sort(
        key=lambda session: (
            session.session_date or "",
            session.started_at or session.created_at,
            session.created_at,
            session.crew_member.code if session.crew_member else "",
        ),
        reverse=True,
    )
    latest_session_by_crew = {}
    session_count_by_crew = {}
    for session in sessions:
        session_count_by_crew[session.crew_member_id] = (
            session_count_by_crew.get(session.crew_member_id, 0) + 1
        )
        latest_session_by_crew.setdefault(session.crew_member_id, session)

    crew_rows = []
    mobile_account_count = 0
    running_count = 0
    data_ready_count = 0
    for crew in crew_queryset.order_by("team__code", "name", "code"):
        mobile_user = _get_optional_related(crew, "mobile_app_user")
        live_status = _get_optional_related(crew, "live_work_status")
        latest_session = latest_session_by_crew.get(crew.id)
        has_mobile_account = bool(mobile_user)
        is_working = bool(
            live_status and live_status.status == live_status.Status.RUNNING
        )
        latest_has_rssi = bool(
            latest_session and getattr(latest_session, "has_rssi_count", 0)
        )
        latest_capture_count = int(
            getattr(latest_session, "capture_count", 0) or 0
        ) if latest_session else 0

        if has_mobile_account:
            mobile_account_count += 1
        if is_working:
            running_count += 1
        if latest_session and latest_has_rssi and latest_capture_count >= 10:
            data_ready_count += 1

        crew_rows.append(
            {
                "id": crew.id,
                "name": crew.name,
                "code": crew.code,
                "team_id": crew.team_id,
                "team_code": crew.team.code if crew.team else "",
                "team_name": crew.team.name if crew.team else "",
                "vehicle_number": crew.vehicle_number or "",
                "has_mobile_account": has_mobile_account,
                "app_version": (
                    (live_status.last_app_version if live_status else "")
                    or (mobile_user.last_app_version if mobile_user else "")
                    or (latest_session.app_version if latest_session else "")
                    or ""
                ),
                "last_login_at": (
                    mobile_user.last_login_at.isoformat()
                    if mobile_user and mobile_user.last_login_at
                    else None
                ),
                "is_working": is_working,
                "background_location_granted": bool(
                    live_status and live_status.background_location_granted
                ),
                "session_count": int(session_count_by_crew.get(crew.id, 0) or 0),
                "latest_session_date": (
                    latest_session.session_date.isoformat()
                    if latest_session
                    else None
                ),
                "latest_uploaded_at": (
                    latest_session.created_at.isoformat()
                    if latest_session
                    else None
                ),
                "latest_capture_count": latest_capture_count,
                "latest_has_rssi": latest_has_rssi,
                "latest_cycle_count": int(latest_session.cycle_count or 0)
                if latest_session
                else 0,
                "latest_distance_m": float(latest_session.distance_m or 0)
                if latest_session
                else 0,
                "csv_available": bool(latest_session),
            }
        )

    session_rows = SessionListSerializer(
        sessions,
        many=True,
        context={"request": request},
    ).data

    return Response(
        {
            "summary": {
                "crew_count": len(crew_rows),
                "mobile_account_count": mobile_account_count,
                "working_count": running_count,
                "data_ready_count": data_ready_count,
                "session_count": len(session_rows),
            },
            "crew_rows": crew_rows,
            "sessions": session_rows,
        }
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def legal_consent_matrix(request):
    forbidden = _admin_required(request)
    if forbidden:
        return forbidden

    team = request.query_params.get("team")
    crew_queryset = CrewMember.objects.filter(
        is_active=True,
        is_yongcha=False,
        team__company_app=get_company_app_from_request(request),
    ).select_related("team", "mobile_app_user")
    if team:
        crew_queryset = crew_queryset.filter(team_id=team)

    crews = list(crew_queryset.order_by("team__code", "name", "code"))
    mobile_user_ids = [
        crew.mobile_app_user.id
        for crew in crews
        if _get_optional_related(crew, "mobile_app_user")
    ]
    document_keys = [item["document_key"] for item in APP_REQUIRED_LEGAL_ITEMS]

    latest_history = {}
    if mobile_user_ids:
        histories = (
            LegalConsentHistory.objects.filter(
                subject_type=LegalConsentHistory.SubjectType.MOBILE_USER,
                mobile_user_id__in=mobile_user_ids,
                document_key__in=document_keys,
            )
            .order_by("mobile_user_id", "document_key", "-agreed_at", "-id")
        )
        for history in histories:
            key = (history.mobile_user_id, history.document_key)
            latest_history.setdefault(key, history)

    rows = []
    mobile_account_count = 0
    all_required_agreed_count = 0
    for crew in crews:
        mobile_user = _get_optional_related(crew, "mobile_app_user")
        if mobile_user:
            mobile_account_count += 1

        consents = {}
        required_ok = True
        for item in APP_REQUIRED_LEGAL_ITEMS:
            history = (
                latest_history.get((mobile_user.id, item["document_key"]))
                if mobile_user
                else None
            )
            fallback_agreed_at = (
                getattr(mobile_user, item["agreed_field"], None)
                if mobile_user
                else None
            )
            agreed = bool(history.agreed if history else fallback_agreed_at)
            if not agreed:
                required_ok = False
            consents[item["key"]] = {
                "label": item["label"],
                "agreed": agreed,
                "version": history.document_version if history else "",
                "agreed_at": (
                    (history.agreed_at if history else fallback_agreed_at).isoformat()
                    if (history or fallback_agreed_at)
                    else None
                ),
                "app_version": history.app_version if history else "",
                "source": "history" if history else ("legacy_field" if fallback_agreed_at else "none"),
            }

        if required_ok and mobile_user:
            all_required_agreed_count += 1

        rows.append(
            {
                "id": crew.id,
                "name": crew.name,
                "code": crew.code,
                "team_id": crew.team_id,
                "team_code": crew.team.code if crew.team else "",
                "team_name": crew.team.name if crew.team else "",
                "vehicle_number": crew.vehicle_number or "",
                "has_mobile_account": bool(mobile_user),
                "mobile_status": mobile_user.status if mobile_user else "",
                "signup_completed": bool(mobile_user and mobile_user.signup_completed),
                "signup_completed_at": (
                    mobile_user.signup_completed_at.isoformat()
                    if mobile_user and mobile_user.signup_completed_at
                    else None
                ),
                "last_app_version": mobile_user.last_app_version if mobile_user else "",
                "all_required_agreed": required_ok and bool(mobile_user),
                "consents": consents,
            }
        )

    return Response(
        {
            "summary": {
                "crew_count": len(rows),
                "mobile_account_count": mobile_account_count,
                "all_required_agreed_count": all_required_agreed_count,
                "missing_required_count": max(mobile_account_count - all_required_agreed_count, 0),
                "current_version": LEGAL_DOCUMENT_VERSION,
            },
            "columns": [
                {
                    "key": item["key"],
                    "label": item["label"],
                    "agreement_key": item["agreement_key"],
                    "document_key": item["document_key"],
                }
                for item in APP_REQUIRED_LEGAL_ITEMS
            ],
            "rows": rows,
        }
    )
