from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Team
from apps.crew.models import CrewMember
from apps.settlement.models import Settlement, SettlementDetail

from .models import MobileAppUser, MobilePassword
from .serializers import (
    MobileApprovalActionSerializer,
    MobileAppUserSerializer,
    MobileLoginSerializer,
    MobilePasswordChangeSerializer,
    MobileRegisterSerializer,
)

DEFAULT_MOBILE_PASSWORD = "0000"


def _normalize_name(name):
    return " ".join(str(name or "").strip().split())


def _get_or_create_mobile_crew(name, team_code):
    """이름+조만으로 모바일 로그인이 가능하도록 팀/기사 레코드를 보장한다."""
    name = _normalize_name(name)
    team_code = str(team_code or "").strip().upper()

    if not name or not team_code:
        raise ValueError("이름과 조 코드를 입력해 주세요.")

    with transaction.atomic():
        team, _ = Team.objects.get_or_create(
            code=team_code,
            defaults={"name": f"{team_code}조", "is_active": True},
        )
        if not team.is_active:
            team.is_active = True
            team.save(update_fields=["is_active"])

        crew = (
            CrewMember.objects.filter(name=name, team=team, is_active=True).first()
            or CrewMember.objects.filter(code=name, team=team).first()
        )

        if crew:
            update_fields = []
            if not crew.is_active:
                crew.is_active = True
                update_fields.append("is_active")
            if crew.name != name:
                crew.name = name
                update_fields.append("name")
            if crew.is_new:
                crew.is_new = False
                update_fields.append("is_new")
            if update_fields:
                crew.save(update_fields=update_fields)
        else:
            crew = CrewMember.objects.create(
                code=name,
                name=name,
                team=team,
                is_active=True,
                is_new=False,
            )

        mobile_user, _ = MobileAppUser.objects.update_or_create(
            crew_member=crew,
            defaults={
                "name": name,
                "team_code": team_code,
                "status": MobileAppUser.Status.APPROVED,
                "approved_at": timezone.now(),
                "approved_by": None,
                "is_active": True,
            },
        )

    return team, crew, mobile_user


def _get_or_create_password_record(mobile_user):
    password_record, _ = MobilePassword.objects.get_or_create(
        mobile_user=mobile_user,
        defaults={
            "password_hash": make_password(DEFAULT_MOBILE_PASSWORD),
            "is_default": True,
        },
    )
    return password_record


def _is_valid_mobile_password(mobile_user, password):
    password_record = _get_or_create_password_record(mobile_user)
    return check_password(password, password_record.password_hash)


# =============================================================================
# 기사용 모바일 API
# =============================================================================


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_register(request):
    """이전 가입 요청 API. 현재는 이름+조 입력 즉시 사용 가능 상태로 만든다."""
    serializer = MobileRegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    name = serializer.validated_data["name"]
    team_code = serializer.validated_data["team_code"]

    try:
        _, _, mobile_user = _get_or_create_mobile_crew(name, team_code)
    except ValueError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {
            "id": mobile_user.id,
            "status": MobileAppUser.Status.APPROVED,
            "message": "바로 로그인할 수 있습니다. 초기 비밀번호는 0000입니다.",
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_status(request):
    """이전 가입 상태 조회 API. 현재는 이름+조가 유효하면 항상 APPROVED."""
    name = request.query_params.get("name", "")
    team_code = request.query_params.get("team_code", "").upper()

    if not name or not team_code:
        return Response(
            {"detail": "이름과 조 코드를 입력해 주세요."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        _get_or_create_mobile_crew(name, team_code)
        return Response({"status": MobileAppUser.Status.APPROVED})
    except ValueError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_login(request):
    """이름+조만으로 바로 로그인하는 API"""
    serializer = MobileLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    name = serializer.validated_data["name"]
    team_code = serializer.validated_data["team_code"]
    password = serializer.validated_data["password"]

    try:
        team, crew, mobile_user = _get_or_create_mobile_crew(name, team_code)
    except ValueError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    password_record = _get_or_create_password_record(mobile_user)

    if not check_password(password, password_record.password_hash):
        return Response(
            {"detail": "비밀번호가 올바르지 않습니다."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # JWT 토큰 발급 — crew_member_id를 커스텀 클레임에 포함
    refresh = RefreshToken()
    refresh["crew_member_id"] = crew.id
    refresh["name"] = crew.name
    refresh["team_code"] = team_code

    # 최근 로그인 갱신
    mobile_user.last_login_at = timezone.now()
    mobile_user.save(update_fields=["last_login_at"])

    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "crew_member_id": crew.id,
        "name": crew.name,
        "team_code": team_code,
        "requires_password_change": password_record.is_default,
    })


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_refresh(request):
    """FR-403: 토큰 갱신 API"""
    refresh_token = request.data.get("refresh")
    if not refresh_token:
        return Response(
            {"detail": "리프레시 토큰이 필요합니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        refresh = RefreshToken(refresh_token)
        return Response({"access": str(refresh.access_token)})
    except Exception:
        return Response(
            {"detail": "토큰이 만료되었습니다. 다시 로그인해 주세요."},
            status=status.HTTP_401_UNAUTHORIZED,
        )


def _get_crew_from_token(request):
    """JWT 토큰에서 crew_member_id를 추출하여 CrewMember 반환"""
    from rest_framework_simplejwt.authentication import JWTAuthentication

    auth = JWTAuthentication()
    try:
        validated_token = auth.get_validated_token(
            auth.get_raw_token(auth.get_header(request))
        )
        crew_member_id = validated_token.get("crew_member_id")
        if not crew_member_id:
            return None
        return CrewMember.objects.get(id=crew_member_id, is_active=True)
    except Exception:
        return None


def _get_mobile_user_from_token(request):
    crew = _get_crew_from_token(request)
    if not crew:
        return None, None

    mobile_user = MobileAppUser.objects.filter(crew_member=crew, is_active=True).first()
    if not mobile_user and crew.team:
        _, _, mobile_user = _get_or_create_mobile_crew(crew.name, crew.team.code)

    return crew, mobile_user


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_change_password(request):
    """로그인된 기사의 앱 비밀번호 변경 API"""
    crew, mobile_user = _get_mobile_user_from_token(request)
    if not crew or not mobile_user:
        return Response(
            {"detail": "세션이 만료되었습니다. 다시 로그인해 주세요."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    serializer = MobilePasswordChangeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    password_record = _get_or_create_password_record(mobile_user)
    if check_password(serializer.validated_data["password"], password_record.password_hash):
        return Response(
            {
                "detail": "\ud604\uc7ac \ube44\ubc00\ubc88\ud638\uc640 \ub2e4\ub978 4\uc790\ub9ac \uc22b\uc790\ub97c \uc785\ub825\ud574 \uc8fc\uc138\uc694."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    password_record.password_hash = make_password(serializer.validated_data["password"])
    password_record.is_default = False
    password_record.changed_at = timezone.now()
    password_record.save(
        update_fields=["password_hash", "is_default", "changed_at", "updated_at"]
    )

    return Response({"detail": "비밀번호가 변경되었습니다."})


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_profile(request):
    """기사 프로필 조회"""
    crew = _get_crew_from_token(request)
    if not crew:
        return Response(
            {"detail": "세션이 만료되었습니다. 다시 로그인해 주세요."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    mobile_user = MobileAppUser.objects.filter(crew_member=crew, is_active=True).first()
    password_record = _get_or_create_password_record(mobile_user) if mobile_user else None

    return Response({
        "name": crew.name,
        "team_code": crew.team.code if crew.team else "",
        "team_name": crew.team.name if crew.team else "",
        "requires_password_change": bool(password_record and password_record.is_default),
    })


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_settlements(request):
    """FR-501: 월별 정산 조회 API"""
    crew = _get_crew_from_token(request)
    if not crew:
        return Response(
            {"detail": "세션이 만료되었습니다. 다시 로그인해 주세요."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    month = request.query_params.get("month", "")
    if not month or len(month) != 7:
        return Response(
            {"detail": "month 파라미터가 필요합니다. (형식: YYYY-MM)"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        year, mon = month.split("-")
        year, mon = int(year), int(mon)
    except (ValueError, AttributeError):
        return Response(
            {"detail": "month 형식이 올바르지 않습니다. (예: 2026-04)"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 확정된(CONFIRMED/PAID) 정산에 속한 해당 기사의 SettlementDetail을 조회
    # dispatch_upload.dispatch_date 기준으로 날짜별 집계
    details = (
        SettlementDetail.objects.filter(
            crew_member=crew,
            settlement__status__in=["CONFIRMED", "PAID"],
            dispatch_upload__dispatch_date__year=year,
            dispatch_upload__dispatch_date__month=mon,
        )
        .values("dispatch_upload__dispatch_date")
        .annotate(
            box_count=Coalesce(Sum("boxes"), Value(0)),
            amount=Coalesce(Sum("pay_amount"), Value(0, output_field=DecimalField())) + Coalesce(Sum("overtime_cost"), Value(0, output_field=DecimalField())),
        )
        .order_by("dispatch_upload__dispatch_date")
    )

    days = []
    total_boxes = 0
    total_amount = 0

    for d in details:
        date = d["dispatch_upload__dispatch_date"]
        box_count = d["box_count"]
        amount = d["amount"]
        days.append({
            "date": date.isoformat() if hasattr(date, "isoformat") else str(date),
            "box_count": box_count,
            "amount": amount,
        })
        total_boxes += box_count
        total_amount += amount

    return Response({
        "days": days,
        "total_boxes": total_boxes,
        "total_amount": total_amount,
    })


# =============================================================================
# 관리자용 승인 API (기존 웹 대시보드에서 사용)
# =============================================================================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_mobile_approvals(request):
    """모바일 앱 가입 승인은 더 이상 사용하지 않으므로 빈 목록을 반환한다."""
    return Response([])


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def admin_mobile_approval_action(request, pk):
    """FR-604: 승인/거절 처리"""
    try:
        mobile_user = MobileAppUser.objects.get(pk=pk)
    except MobileAppUser.DoesNotExist:
        return Response(
            {"detail": "요청을 찾을 수 없습니다."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = MobileApprovalActionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    action = serializer.validated_data["action"]
    if action == "approve":
        mobile_user.status = MobileAppUser.Status.APPROVED
        mobile_user.approved_at = timezone.now()
        mobile_user.approved_by = request.user
    else:
        mobile_user.status = MobileAppUser.Status.REJECTED

    mobile_user.save()
    return Response(MobileAppUserSerializer(mobile_user).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_mobile_users(request):
    """FR-603: 승인 기사 목록"""
    team_code = request.query_params.get("team_code")
    status_filter = request.query_params.get("status", "APPROVED")

    qs = MobileAppUser.objects.filter(status=status_filter)
    if team_code:
        qs = qs.filter(team_code=team_code.upper())

    serializer = MobileAppUserSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def admin_mobile_user_deactivate(request, pk):
    """앱 접근 비활성화 (소프트 삭제)"""
    try:
        mobile_user = MobileAppUser.objects.get(pk=pk)
    except MobileAppUser.DoesNotExist:
        return Response(
            {"detail": "사용자를 찾을 수 없습니다."},
            status=status.HTTP_404_NOT_FOUND,
        )

    mobile_user.is_active = False
    mobile_user.save(update_fields=["is_active"])
    return Response(status=status.HTTP_204_NO_CONTENT)
