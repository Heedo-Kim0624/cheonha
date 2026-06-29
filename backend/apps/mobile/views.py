from datetime import date as date_cls, timedelta
from decimal import Decimal, ROUND_HALF_UP
import logging

import jwt
from django.contrib.auth.hashers import check_password, make_password
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Shipper, Team
from apps.crew.models import CrewMember
from apps.dispatch.models import DispatchRecord
from apps.inquiry.models import InquiryMessage, SettlementInquiry
from apps.inquiry.serializers import InquiryMessageSerializer
from apps.settlement.models import Settlement, SettlementDetail
from apps.tracking.services import (
    MobileTrackingUploadError,
    get_or_create_tracking_session_stub,
    heartbeat_live_work_session,
    import_mobile_tracking_session,
    mark_live_work_session_started,
    mark_live_work_session_stopped,
    process_tracking_session_async,
    save_raw_tracking_csv,
    summarize_mobile_tracking_upload,
)
from apps.points.services import (
    evaluate_tracking_point_award,
    evaluate_tracking_point_award_from_metrics,
)

from .app_messages import (
    sanitize_mobile_app_message_overrides,
)
from .models import (
    LegalConsentHistory,
    MobileAppMessageConfig,
    MobileAppUser,
    MobileWorkSessionCheckpoint,
    MobilePassword,
    record_legal_consent_history,
)
from .serializers import (
    MobileAdminAppConfigSerializer,
    MobileAdminAppConfigWriteSerializer,
    MobileApprovalActionSerializer,
    MobileAppConfigSerializer,
    MobileAppUserSerializer,
    MobileSettlementInquiryCommentSerializer,
    MobileSettlementInquiryReadSerializer,
    MobileSettlementInquiryRequestSerializer,
    MobileLoginSerializer,
    MobilePasswordChangeSerializer,
    MobilePayrollAccountSerializer,
    MobileSignupCompleteSerializer,
    MobileVehicleNumberSerializer,
    MobileVehicleInspectionDateSerializer,
    MobileRegisterSerializer,
    MobileWorkSessionLiveSerializer,
    MobileWorkSessionUploadSerializer,
    get_mobile_app_message_sections,
)

DEFAULT_MOBILE_PASSWORD = "0000"
SESSION_EXPIRED_DETAIL = "세션이 만료되었습니다. 다시 로그인해 주세요."
MISSING_LOGIN_FIELDS_DETAIL = "이름과 조 코드를 입력해 주세요."
logger = logging.getLogger(__name__)


def _is_admin_user(user):
    return bool(
        user
        and user.is_authenticated
        and (user.is_staff or getattr(user, "is_admin", lambda: False)())
    )


def _admin_required(request):
    if not _is_admin_user(request.user):
        return Response(
            {"detail": "관리자 권한이 필요합니다."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


def _get_mobile_app_message_config():
    return MobileAppMessageConfig.get_solo()


def _serialize_mobile_app_config_payload(include_sections=False):
    config = _get_mobile_app_message_config()
    payload = {
        "messages": config.merged_messages,
        "updated_at": config.updated_at,
    }
    if include_sections:
        payload["sections"] = get_mobile_app_message_sections()
    return payload


def _normalize_name(name):
    return " ".join(str(name or "").strip().split())


def _get_or_create_mobile_crew(name, team_code):
    """기존 서버 배송원만 모바일 앱 계정과 연결한다."""
    name = _normalize_name(name)
    team_code = str(team_code or "").strip().upper()

    if not name or not team_code:
        raise ValueError(MISSING_LOGIN_FIELDS_DETAIL)

    with transaction.atomic():
        team = Team.objects.filter(code=team_code, company_app="cheonha").first()
        if not team:
            raise ValueError("서버에 등록된 조가 아닙니다. 관리자에게 확인해주세요.")
        if not team.is_active:
            team.is_active = True
            team.save(update_fields=["is_active"])

        crew = (
            CrewMember.objects.filter(name=name, team=team, is_active=True).first()
            or CrewMember.objects.filter(code=name, team=team, is_active=True).first()
        )

        if not crew:
            raise ValueError("서버에 등록된 배송원 이름이 아닙니다. 배송원 관리에서 먼저 확인해주세요.")

        if crew.is_new:
            crew.is_new = False
            crew.save(update_fields=["is_new", "updated_at"])

        mobile_user, _ = MobileAppUser.objects.update_or_create(
            crew_member=crew,
            defaults={
                "name": crew.name,
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


def _update_crew_vehicle_number(crew, vehicle_number):
    normalized = str(vehicle_number or "").strip()
    if not normalized or crew.vehicle_number == normalized:
        return normalized

    crew.vehicle_number = normalized
    crew.save(update_fields=["vehicle_number", "updated_at"])
    return normalized


def _update_crew_payroll_account(crew, bank_name, bank_account_number):
    normalized_bank_name = str(bank_name or "").strip()
    normalized_account_number = str(bank_account_number or "").strip()

    update_fields = []
    if crew.bank_name != normalized_bank_name:
        crew.bank_name = normalized_bank_name
        update_fields.append("bank_name")
    if crew.bank_account_number != normalized_account_number:
        crew.bank_account_number = normalized_account_number
        update_fields.append("bank_account_number")

    if update_fields:
        update_fields.append("updated_at")
        crew.save(update_fields=update_fields)

    return {
        "bank_name": crew.bank_name or "",
        "bank_account_number": crew.bank_account_number or "",
    }


def _update_crew_vehicle_inspection_date(crew, inspection_date):
    if crew.vehicle_inspection_date != inspection_date:
        crew.vehicle_inspection_date = inspection_date
        crew.save(update_fields=["vehicle_inspection_date", "updated_at"])

    return crew.vehicle_inspection_date


def _issue_mobile_tokens(crew, team_code):
    refresh = RefreshToken()
    refresh["crew_member_id"] = crew.id
    refresh["name"] = crew.name
    refresh["team_code"] = team_code
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "crew_member_id": crew.id,
        "name": crew.name,
        "team_code": team_code,
        "vehicle_number": crew.vehicle_number or "",
    }


def _complete_mobile_signup(
    mobile_user,
    crew,
    *,
    password,
    vehicle_number,
    agree_privacy_policy,
    agree_terms,
    agree_data_processing,
    agree_location_terms,
    agree_marketing_event,
    app_version="",
    request=None,
):
    now = timezone.now()
    password_record = _get_or_create_password_record(mobile_user)
    password_record.password_hash = make_password(password)
    password_record.is_default = False
    password_record.changed_at = now
    password_record.save(
        update_fields=["password_hash", "is_default", "changed_at", "updated_at"]
    )

    _update_crew_vehicle_number(crew, vehicle_number)

    update_fields = ["signup_completed"]
    mobile_user.signup_completed = True
    if mobile_user.signup_completed_at is None:
        mobile_user.signup_completed_at = now
        update_fields.append("signup_completed_at")
    if agree_privacy_policy:
        mobile_user.privacy_policy_agreed_at = now
        update_fields.append("privacy_policy_agreed_at")
    if agree_terms:
        mobile_user.terms_agreed_at = now
        update_fields.append("terms_agreed_at")
    if agree_data_processing:
        mobile_user.third_party_information_agreed_at = now
        update_fields.append("third_party_information_agreed_at")
    if agree_location_terms:
        mobile_user.location_terms_agreed_at = now
        update_fields.append("location_terms_agreed_at")
    if agree_marketing_event:
        mobile_user.marketing_event_agreed_at = now
        update_fields.append("marketing_event_agreed_at")
    mobile_user.save(update_fields=update_fields)

    subject_identifier = f"{mobile_user.name}/{mobile_user.team_code}"
    consent_rows = [
        ("agree_terms", "app_terms", bool(agree_terms)),
        ("agree_privacy_policy", "privacy_policy", bool(agree_privacy_policy)),
        ("agree_location_terms", "location_terms", bool(agree_location_terms)),
        ("agree_data_processing", "data_processing", bool(agree_data_processing)),
        ("agree_marketing_event", "marketing_consent", bool(agree_marketing_event)),
    ]
    for agreement_key, document_key, agreed in consent_rows:
        record_legal_consent_history(
            subject_type=LegalConsentHistory.SubjectType.MOBILE_USER,
            subject_identifier=subject_identifier,
            mobile_user=mobile_user,
            agreement_key=agreement_key,
            document_key=document_key,
            agreed=agreed,
            agreed_at=now,
            app_version=app_version,
            request=request,
        )

    return password_record


def _get_data_processing_agreement(validated_data):
    return bool(
        validated_data.get("agree_data_processing")
        or validated_data.get("agree_third_party_information")
    )


# =============================================================================
# 湲곗궗??紐⑤컮??API
# =============================================================================


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_app_config(request):
    serializer = MobileAppConfigSerializer(
        _serialize_mobile_app_config_payload(include_sections=False)
    )
    return Response(serializer.data)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_register(request):
    """회원가입 API. 이름과 조가 기존 시스템에 존재하면 자동 승인한다."""
    serializer = MobileRegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    name = serializer.validated_data["name"]
    team_code = serializer.validated_data["team_code"]
    password = serializer.validated_data["password"]
    vehicle_number = serializer.validated_data["vehicle_number"]

    try:
        _, crew, mobile_user = _get_or_create_mobile_crew(name, team_code)
    except ValueError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    password_record = _complete_mobile_signup(
        mobile_user,
        crew,
        password=password,
        vehicle_number=vehicle_number,
        agree_privacy_policy=serializer.validated_data["agree_privacy_policy"],
        agree_terms=serializer.validated_data["agree_terms"],
        agree_data_processing=_get_data_processing_agreement(serializer.validated_data),
        agree_location_terms=serializer.validated_data["agree_location_terms"],
        agree_marketing_event=serializer.validated_data.get("agree_marketing_event"),
        app_version=serializer.validated_data.get("app_version", ""),
        request=request,
    )
    recorded_app_version = _record_mobile_app_version(crew, serializer.validated_data.get("app_version", ""))
    if recorded_app_version:
        mobile_user.last_app_version = recorded_app_version
    mobile_user.last_login_at = timezone.now()
    mobile_user.save(update_fields=["last_login_at"])

    payload = _issue_mobile_tokens(crew, team_code)
    payload.update(
        {
            "status": MobileAppUser.Status.APPROVED,
            "requires_password_change": password_record.is_default,
            "signup_completed": mobile_user.signup_completed,
            "detail": "회원가입이 완료되었습니다.",
        }
    )
    return Response(
        payload,
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_status(request):
    """?댁쟾 媛???곹깭 議고쉶 API. ?꾩옱???대쫫+議곌? ?좏슚?섎㈃ ??긽 APPROVED."""
    name = request.query_params.get("name", "")
    team_code = request.query_params.get("team_code", "").upper()

    if not name or not team_code:
        return Response(
            {"detail": MISSING_LOGIN_FIELDS_DETAIL},
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
    """?대쫫+議곕쭔?쇰줈 諛붾줈 濡쒓렇?명븯??API"""
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

    # JWT ?좏겙 諛쒓툒 ??crew_member_id瑜?而ㅼ뒪? ?대젅?꾩뿉 ?ы븿
    recorded_app_version = _record_mobile_app_version(crew, serializer.validated_data.get("app_version", ""))
    if recorded_app_version:
        mobile_user.last_app_version = recorded_app_version
    mobile_user.last_login_at = timezone.now()
    mobile_user.save(update_fields=["last_login_at"])

    payload = _issue_mobile_tokens(crew, team_code)
    payload.update(
        {
            "requires_password_change": password_record.is_default,
            "signup_completed": mobile_user.signup_completed,
        }
    )
    return Response(payload)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_complete_signup(request):
    crew, mobile_user = _get_mobile_user_from_token(request)
    if not crew or not mobile_user:
        return Response(
            {"detail": SESSION_EXPIRED_DETAIL},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    serializer = MobileSignupCompleteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    _complete_mobile_signup(
        mobile_user,
        crew,
        password=serializer.validated_data["password"],
        vehicle_number=serializer.validated_data["vehicle_number"],
        agree_privacy_policy=serializer.validated_data["agree_privacy_policy"],
        agree_terms=serializer.validated_data["agree_terms"],
        agree_data_processing=_get_data_processing_agreement(serializer.validated_data),
        agree_location_terms=serializer.validated_data["agree_location_terms"],
        agree_marketing_event=serializer.validated_data.get("agree_marketing_event"),
        app_version=serializer.validated_data.get("app_version", ""),
        request=request,
    )
    recorded_app_version = _record_mobile_app_version(crew, serializer.validated_data.get("app_version", ""))
    if recorded_app_version:
        mobile_user.last_app_version = recorded_app_version

    return Response(
        {
            "name": crew.name,
            "team_code": crew.team.code if crew.team else "",
            "team_name": crew.team.name if crew.team else "",
            "vehicle_number": crew.vehicle_number or "",
            "bank_name": crew.bank_name or "",
            "bank_account_number": crew.bank_account_number or "",
            "vehicle_inspection_date": (
                crew.vehicle_inspection_date.isoformat()
                if crew.vehicle_inspection_date
                else None
            ),
            "requires_password_change": False,
            "signup_completed": True,
            "privacy_policy_agreed_at": mobile_user.privacy_policy_agreed_at,
            "terms_agreed_at": mobile_user.terms_agreed_at,
            "third_party_information_agreed_at": mobile_user.third_party_information_agreed_at,
            "location_terms_agreed_at": mobile_user.location_terms_agreed_at,
            "marketing_event_agreed_at": mobile_user.marketing_event_agreed_at,
            "app_version": mobile_user.last_app_version,
        }
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_refresh(request):
    """FR-403: ?좏겙 媛깆떊 API"""
    refresh_token = request.data.get("refresh")
    if not refresh_token:
        return Response(
            {"detail": "리프레시 토큰이 필요합니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        refresh = RefreshToken(refresh_token)
        new_refresh = RefreshToken()
        for claim in ("crew_member_id", "name", "team_code"):
            if claim in refresh:
                new_refresh[claim] = refresh[claim]
        return Response(
            {
                "access": str(new_refresh.access_token),
                "refresh": str(new_refresh),
            }
        )
    except Exception:
        return Response(
            {"detail": SESSION_EXPIRED_DETAIL},
            status=status.HTTP_401_UNAUTHORIZED,
        )


def _get_crew_from_token(request, *, allow_expired_recovery=False):
    """JWT ?좏겙?먯꽌 crew_member_id瑜?異붿텧?섏뿬 CrewMember 諛섑솚"""
    from rest_framework_simplejwt.authentication import JWTAuthentication

    auth = JWTAuthentication()
    try:
        raw_token = auth.get_raw_token(auth.get_header(request))
        validated_token = auth.get_validated_token(raw_token)
        crew_member_id = validated_token.get("crew_member_id")
        if not crew_member_id:
            return None
        return CrewMember.objects.get(id=crew_member_id, is_active=True)
    except Exception:
        if not allow_expired_recovery:
            return None

    try:
        raw_token = auth.get_raw_token(auth.get_header(request))
        if not raw_token:
            return None
        token_text = raw_token.decode("utf-8") if isinstance(raw_token, bytes) else str(raw_token)
        signing_key = (
            api_settings.VERIFYING_KEY
            if str(api_settings.ALGORITHM).startswith("RS")
            else api_settings.SIGNING_KEY
        )
        decode_kwargs = {
            "key": signing_key,
            "algorithms": [api_settings.ALGORITHM],
            "options": {"verify_exp": False},
        }
        if api_settings.AUDIENCE is not None:
            decode_kwargs["audience"] = api_settings.AUDIENCE
        if api_settings.ISSUER is not None:
            decode_kwargs["issuer"] = api_settings.ISSUER

        payload = jwt.decode(token_text, **decode_kwargs)
        if payload.get(api_settings.TOKEN_TYPE_CLAIM) != "access":
            return None
        crew_member_id = payload.get("crew_member_id")
        if not crew_member_id:
            return None
        crew = CrewMember.objects.get(id=crew_member_id, is_active=True)
        logger.warning(
            "Accepted expired mobile access token for work-session recovery: crew_id=%s",
            crew.id,
        )
        return crew
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


def _record_mobile_app_version(crew, app_version):
    normalized = str(app_version or "").strip()[:40]
    if not normalized or not crew:
        return ""
    MobileAppUser.objects.filter(crew_member=crew, is_active=True).update(
        last_app_version=normalized,
    )
    return normalized


def _get_inquiry_badge_status(inquiry):
    if not inquiry:
        return None
    if inquiry.last_by == "crew" and inquiry.status == "OPEN":
        return "pending"
    if inquiry.status in {"ANSWERED", "READ"}:
        return "answered"
    return None


def _quantize_whole(value):
    return int(Decimal(value or 0).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _get_settlement_day_snapshot(crew, target_date):
    details = SettlementDetail.objects.filter(
        crew_member=crew,
        settlement__status__in=["CONFIRMED", "PAID"],
        dispatch_upload__dispatch_date=target_date,
    )

    aggregates = details.aggregate(
        box_count=Coalesce(Sum("boxes"), Value(0)),
        pay_total=Coalesce(
            Sum("pay_amount"),
            Value(0, output_field=DecimalField()),
        ),
        adjustment_amount=Coalesce(
            Sum("overtime_cost"),
            Value(0, output_field=DecimalField()),
        ),
    )

    box_count = int(aggregates["box_count"] or 0)
    pay_total = Decimal(aggregates["pay_total"] or 0)
    adjustment_amount = Decimal(aggregates["adjustment_amount"] or 0)
    total_amount = pay_total + adjustment_amount

    if box_count <= 0 and total_amount <= 0:
        return None

    if box_count > 0:
        pay_price = (pay_total / Decimal(box_count)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    else:
        pay_price = Decimal("0")

    return {
        "dispatch_date": target_date,
        "box_count": box_count,
        "pay_price": pay_price,
        "adjustment_amount": adjustment_amount,
        "total_amount": total_amount,
        "is_overtime": adjustment_amount != 0,
    }


def _build_mobile_inquiry_payload(inquiry, snapshot):
    active_snapshot = snapshot or {}

    if inquiry:
        box_count = int(inquiry.boxes)
        adjustment_amount = _quantize_whole(inquiry.adjustment_amount)
        total_amount = _quantize_whole(inquiry.total_amount)
        pay_price = _quantize_whole(inquiry.pay_price)
        status = inquiry.status
        inquiry_id = inquiry.id
        last_by = inquiry.last_by
        messages = InquiryMessageSerializer(inquiry.messages.all(), many=True).data
        badge_status = _get_inquiry_badge_status(inquiry)
        dispatch_date = inquiry.dispatch_date
        updated_at = inquiry.updated_at.isoformat() if inquiry.updated_at else None
    else:
        box_count = int(active_snapshot.get("box_count") or 0)
        adjustment_amount = _quantize_whole(active_snapshot.get("adjustment_amount"))
        total_amount = _quantize_whole(active_snapshot.get("total_amount"))
        pay_price = _quantize_whole(active_snapshot.get("pay_price"))
        status = None
        inquiry_id = None
        last_by = None
        messages = []
        badge_status = None
        dispatch_date = active_snapshot.get("dispatch_date")
        updated_at = None

    return {
        "inquiry_id": inquiry_id,
        "date": dispatch_date.isoformat() if hasattr(dispatch_date, "isoformat") else str(dispatch_date),
        "box_count": box_count,
        "pay_price": pay_price,
        "adjustment_amount": adjustment_amount,
        "amount": total_amount,
        "is_overtime": bool(inquiry.is_overtime if inquiry else active_snapshot.get("is_overtime")),
        "status": status,
        "last_by": last_by,
        "badge_status": badge_status,
        "updated_at": updated_at,
        "messages": messages,
    }


def _serialize_live_work_status(status):
    return {
        "status": status.status,
        "vehicle_number": status.current_vehicle_number or "",
        "session_started_at": (
            status.session_started_at.isoformat() if status.session_started_at else None
        ),
        "session_ended_at": (
            status.session_ended_at.isoformat() if status.session_ended_at else None
        ),
        "last_seen_at": status.last_seen_at.isoformat() if status.last_seen_at else None,
        "background_location_granted": bool(status.background_location_granted),
        "app_version": status.last_app_version or "",
    }


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_change_password(request):
    """濡쒓렇?몃맂 湲곗궗????鍮꾨?踰덊샇 蹂寃?API"""
    crew, mobile_user = _get_mobile_user_from_token(request)
    if not crew or not mobile_user:
        return Response(
            {"detail": SESSION_EXPIRED_DETAIL},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    serializer = MobilePasswordChangeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    password_record = _get_or_create_password_record(mobile_user)
    if check_password(serializer.validated_data["password"], password_record.password_hash):
        return Response(
            {
                "detail": "현재 비밀번호와 다른 4자리 숫자를 입력해 주세요."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    password_record.password_hash = make_password(serializer.validated_data["password"])
    password_record.is_default = False
    password_record.changed_at = timezone.now()
    password_record.save(
        update_fields=['password_hash', 'is_default', 'changed_at', 'updated_at']
    )

    if 'vehicle_number' in serializer.validated_data:
        _update_crew_vehicle_number(
            crew,
            serializer.validated_data.get('vehicle_number', ''),
        )

    return Response({"detail": "비밀번호가 변경되었습니다."})


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_profile(request):
    """湲곗궗 ?꾨줈??議고쉶"""
    crew = _get_crew_from_token(request)
    if not crew:
        return Response(
            {"detail": SESSION_EXPIRED_DETAIL},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    mobile_user = MobileAppUser.objects.filter(crew_member=crew, is_active=True).first()
    password_record = _get_or_create_password_record(mobile_user) if mobile_user else None

    return Response(
        {
            "name": crew.name,
            "team_code": crew.team.code if crew.team else "",
            "team_name": crew.team.name if crew.team else "",
            "vehicle_number": crew.vehicle_number or "",
            "bank_name": crew.bank_name or "",
            "bank_account_number": crew.bank_account_number or "",
            "vehicle_inspection_date": (
                crew.vehicle_inspection_date.isoformat()
                if crew.vehicle_inspection_date
                else None
            ),
            "requires_password_change": bool(password_record and password_record.is_default),
            "signup_completed": bool(mobile_user and mobile_user.signup_completed),
            "privacy_policy_agreed_at": (
                mobile_user.privacy_policy_agreed_at.isoformat()
                if mobile_user and mobile_user.privacy_policy_agreed_at
                else None
            ),
            "terms_agreed_at": (
                mobile_user.terms_agreed_at.isoformat()
                if mobile_user and mobile_user.terms_agreed_at
                else None
            ),
            "third_party_information_agreed_at": (
                mobile_user.third_party_information_agreed_at.isoformat()
                if mobile_user and mobile_user.third_party_information_agreed_at
                else None
            ),
            "location_terms_agreed_at": (
                mobile_user.location_terms_agreed_at.isoformat()
                if mobile_user and mobile_user.location_terms_agreed_at
                else None
            ),
            "marketing_event_agreed_at": (
                mobile_user.marketing_event_agreed_at.isoformat()
                if mobile_user and mobile_user.marketing_event_agreed_at
                else None
            ),
            "app_version": mobile_user.last_app_version if mobile_user else "",
        }
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_update_vehicle_number(request):
    crew = _get_crew_from_token(request)
    if not crew:
        return Response(
            {"detail": SESSION_EXPIRED_DETAIL},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    serializer = MobileVehicleNumberSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    return Response(
        {
            "vehicle_number": _update_crew_vehicle_number(
                crew,
                serializer.validated_data["vehicle_number"],
            )
        }
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_update_payroll_account(request):
    crew = _get_crew_from_token(request)
    if not crew:
        return Response(
            {"detail": SESSION_EXPIRED_DETAIL},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    serializer = MobilePayrollAccountSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    return Response(
        _update_crew_payroll_account(
            crew,
            serializer.validated_data["bank_name"],
            serializer.validated_data["bank_account_number"],
        )
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_update_vehicle_inspection_date(request):
    crew = _get_crew_from_token(request)
    if not crew:
        return Response(
            {"detail": SESSION_EXPIRED_DETAIL},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    serializer = MobileVehicleInspectionDateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    inspection_date = _update_crew_vehicle_inspection_date(
        crew,
        serializer.validated_data["vehicle_inspection_date"],
    )

    return Response(
        {
            "vehicle_inspection_date": (
                inspection_date.isoformat() if inspection_date else None
            )
        }
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_work_session_start(request):
    crew = _get_crew_from_token(request)
    if not crew:
        return Response(
            {"detail": SESSION_EXPIRED_DETAIL},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    serializer = MobileWorkSessionLiveSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    app_version = serializer.validated_data.get("app_version", "")
    _record_mobile_app_version(crew, app_version)
    live_status = mark_live_work_session_started(
        crew=crew,
        vehicle_number=serializer.validated_data.get("vehicle_number", ""),
        background_location_granted=serializer.validated_data.get(
            "background_location_granted",
            False,
        ),
        app_version=app_version,
    )
    return Response(_serialize_live_work_status(live_status))


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_work_session_heartbeat(request):
    crew = _get_crew_from_token(request)
    if not crew:
        return Response(
            {"detail": SESSION_EXPIRED_DETAIL},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    serializer = MobileWorkSessionLiveSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    app_version = serializer.validated_data.get("app_version", "")
    _record_mobile_app_version(crew, app_version)
    live_status = heartbeat_live_work_session(
        crew=crew,
        vehicle_number=serializer.validated_data.get("vehicle_number", ""),
        background_location_granted=serializer.validated_data.get(
            "background_location_granted"
        ),
        app_version=app_version,
    )
    return Response(_serialize_live_work_status(live_status))


def _mobile_work_session_checkpoint_path(crew_id: int) -> str:
    return f"mobile_work_session_checkpoints/crew_{crew_id}.csv"


def _count_mobile_work_session_samples(csv_content: str) -> int:
    lines = [line for line in str(csv_content or "").splitlines() if line.strip()]
    if not lines:
        return 0
    return max(0, len(lines) - 1)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_work_session_checkpoint(request):
    crew = _get_crew_from_token(request, allow_expired_recovery=True)
    if not crew:
        return Response(
            {"detail": SESSION_EXPIRED_DETAIL},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    serializer = MobileWorkSessionUploadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    csv_content = serializer.validated_data["csv_content"]
    vehicle_number = serializer.validated_data.get("vehicle_number", "")
    file_name = serializer.validated_data.get("file_name", "")
    app_version = serializer.validated_data.get("app_version", "")
    background_location_granted = bool(request.data.get("background_location_granted", False))
    _record_mobile_app_version(crew, app_version)

    csv_bytes = len(str(csv_content or "").encode("utf-8"))
    sample_count = _count_mobile_work_session_samples(csv_content)
    checkpoint_path = _mobile_work_session_checkpoint_path(crew.id)

    try:
        if default_storage.exists(checkpoint_path):
            default_storage.delete(checkpoint_path)
        default_storage.save(checkpoint_path, ContentFile(str(csv_content or "").encode("utf-8")))
    except Exception:
        logger.exception("Failed to save mobile work session checkpoint for crew %s", crew.id)
        return Response(
            {"detail": "근무 기록 임시 저장에 실패했습니다."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    checkpoint, _ = MobileWorkSessionCheckpoint.objects.update_or_create(
        crew_member=crew,
        defaults={
            "vehicle_number": vehicle_number,
            "file_name": file_name,
            "csv_path": checkpoint_path,
            "sample_count": sample_count,
            "csv_bytes": csv_bytes,
            "app_version": app_version,
            "background_location_granted": background_location_granted,
            "last_synced_at": timezone.now(),
        },
    )

    heartbeat_live_work_session(
        crew=crew,
        vehicle_number=vehicle_number,
        background_location_granted=background_location_granted,
        app_version=app_version,
    )

    return Response(
        {
            "checkpoint_id": checkpoint.id,
            "sample_count": checkpoint.sample_count,
            "csv_bytes": checkpoint.csv_bytes,
            "last_synced_at": checkpoint.last_synced_at.isoformat(),
        }
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_work_session_stop(request):
    crew = _get_crew_from_token(request, allow_expired_recovery=True)
    if not crew:
        return Response(
            {"detail": SESSION_EXPIRED_DETAIL},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    serializer = MobileWorkSessionLiveSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    app_version = serializer.validated_data.get("app_version", "")
    _record_mobile_app_version(crew, app_version)
    live_status = mark_live_work_session_stopped(
        crew=crew,
        vehicle_number=serializer.validated_data.get("vehicle_number", ""),
        background_location_granted=serializer.validated_data.get(
            "background_location_granted"
        ),
        app_version=app_version,
    )
    return Response(_serialize_live_work_status(live_status))


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_work_session_upload(request):
    crew = _get_crew_from_token(request, allow_expired_recovery=True)
    if not crew:
        return Response(
            {"detail": SESSION_EXPIRED_DETAIL},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    serializer = MobileWorkSessionUploadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    csv_content = serializer.validated_data["csv_content"]
    vehicle_number = serializer.validated_data.get("vehicle_number", "")
    file_name = serializer.validated_data.get("file_name", "")
    app_version = serializer.validated_data.get("app_version", "")
    _record_mobile_app_version(crew, app_version)

    try:
        summary = summarize_mobile_tracking_upload(
            csv_content=csv_content,
            source_name=file_name,
        )
        session, _ = get_or_create_tracking_session_stub(
            crew=crew,
            summary=summary,
            vehicle_number=vehicle_number,
            app_version=app_version,
        )
    except MobileTrackingUploadError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        save_raw_tracking_csv(session, csv_content)
    except Exception:
        logger.exception("Failed to save raw mobile tracking CSV for session %s", session.id)

    try:
        point_award = evaluate_tracking_point_award_from_metrics(
            session=session,
            has_rssi=summary.has_rssi,
            camera_end_count=summary.camera_end_count,
        )
    except Exception:
        logger.exception("Failed to evaluate point award for session %s", session.id)
        point_award = {
            "awarded": False,
            "points": 0,
            "reason": "award_error",
            "balance": 0,
        }

    try:
        process_tracking_session_async(
            session_id=session.id,
            csv_content=csv_content,
            vehicle_number=vehicle_number,
        )
    except Exception:
        logger.exception("Failed to enqueue tracking session processing for session %s", session.id)

    try:
        mark_live_work_session_stopped(
            crew=crew,
            vehicle_number=vehicle_number,
            ended_at=session.ended_at,
            app_version=app_version,
        )
    except Exception:
        logger.exception("Failed to stop live work status for crew %s", crew.id)

    try:
        checkpoint = getattr(crew, "mobile_work_session_checkpoint", None)
        if checkpoint:
            if checkpoint.csv_path and default_storage.exists(checkpoint.csv_path):
                default_storage.delete(checkpoint.csv_path)
            checkpoint.delete()
    except Exception:
        logger.exception("Failed to clear mobile work session checkpoint for crew %s", crew.id)

    return Response(
        {
            "session_id": session.id,
            "session_date": session.session_date.isoformat(),
            "started_at": session.started_at.isoformat(),
            "ended_at": session.ended_at.isoformat(),
            "cycle_count": session.cycle_count,
            "point_awarded": bool(point_award.get("awarded")),
            "point_award_points": int(point_award.get("points") or 0),
            "point_award_reason": point_award.get("reason") or "",
            "point_balance": int(point_award.get("balance") or 0),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_settlements(request):
    """FR-501: ?붾퀎 ?뺤궛 議고쉶 API"""
    crew = _get_crew_from_token(request)
    if not crew:
        return Response(
            {"detail": SESSION_EXPIRED_DETAIL},
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

    # ?뺤젙??CONFIRMED/PAID) ?뺤궛???랁븳 ?대떦 湲곗궗??SettlementDetail??議고쉶
    # dispatch_upload.dispatch_date 湲곗??쇰줈 ?좎쭨蹂?吏묎퀎
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
            adjustment_amount=Coalesce(
                Sum("overtime_cost"),
                Value(0, output_field=DecimalField()),
            ),
            amount=Coalesce(
                Sum("pay_amount"),
                Value(0, output_field=DecimalField()),
            )
            + Coalesce(Sum("overtime_cost"), Value(0, output_field=DecimalField())),
        )
        .order_by("dispatch_upload__dispatch_date")
    )

    detail_rows = list(
        SettlementDetail.objects.filter(
            crew_member=crew,
            settlement__status__in=["CONFIRMED", "PAID"],
            dispatch_upload__dispatch_date__year=year,
            dispatch_upload__dispatch_date__month=mon,
        )
        .select_related("dispatch_upload")
        .order_by("dispatch_upload__dispatch_date", "dispatch_upload__round_no", "dispatch_upload_id", "id")
    )

    upload_round_map = {}
    upload_ids = set()
    shipper_codes = set()
    for detail in detail_rows:
        if not detail.dispatch_upload_id:
            continue
        shipper_code = getattr(detail.dispatch_upload, "shipper_code", None) or getattr(detail, "shipper_code", None) or "kurly"
        upload_ids.add(detail.dispatch_upload_id)
        shipper_codes.add(shipper_code)
        bucket = upload_round_map.setdefault(
            detail.dispatch_upload_id,
            {
                "date": detail.dispatch_upload.dispatch_date,
                "round_no": detail.dispatch_upload.round_no,
                "shipper_code": shipper_code,
                "box_count": 0,
                "amount": 0,
                "is_yongcha": False,
            },
        )
        bucket["box_count"] += int(detail.boxes or 0)
        bucket["amount"] += _quantize_whole(detail.pay_amount or 0)
        bucket["is_yongcha"] = bucket["is_yongcha"] or bool(detail.is_yongcha)

    household_map = {}
    crew_names = [name for name in {str(crew.name or "").strip(), str(crew.code or "").strip()} if name]
    if upload_ids and crew_names:
        for row in (
            DispatchRecord.objects.filter(
                upload_id__in=upload_ids,
                is_valid=True,
                manager_name__in=crew_names,
            )
            .values("upload_id")
            .annotate(household_count=Coalesce(Sum("households"), Value(0)))
        ):
            household_map[row["upload_id"]] = int(row["household_count"] or 0)

    shipper_name_map = {
        item.code: item.name
        for item in Shipper.objects.filter(code__in=shipper_codes)
    }
    round_summaries_by_date = {}
    for upload_id, payload in upload_round_map.items():
        dispatch_date = payload["date"]
        if not dispatch_date:
            continue
        round_summaries_by_date.setdefault(dispatch_date, []).append(
            {
                "round_no": payload["round_no"],
                "shipper_code": payload.get("shipper_code") or "kurly",
                "shipper_name": shipper_name_map.get(payload.get("shipper_code") or "kurly", payload.get("shipper_code") or "kurly"),
                "box_count": payload["box_count"],
                "household_count": household_map.get(upload_id, 0),
                "amount": payload["amount"],
                "is_yongcha": bool(payload["is_yongcha"]),
            }
        )

    inquiry_map = {
        inquiry.dispatch_date: inquiry
        for inquiry in SettlementInquiry.objects.filter(
            crew_member=crew,
            dispatch_date__year=year,
            dispatch_date__month=mon,
        )
    }

    days = []
    total_boxes = 0
    total_amount = 0

    for d in details:
        date = d["dispatch_upload__dispatch_date"]
        box_count = int(d["box_count"] or 0)
        amount = _quantize_whole(d["amount"])
        inquiry = inquiry_map.get(date)
        days.append({
            "date": date.isoformat() if hasattr(date, "isoformat") else str(date),
            "box_count": box_count,
            "adjustment_amount": _quantize_whole(d["adjustment_amount"]),
            "amount": amount,
            "round_summaries": sorted(
                round_summaries_by_date.get(date, []),
                key=lambda item: (item["round_no"] or 99, item["is_yongcha"]),
            ),
            "inquiry_updated_at": inquiry.updated_at.isoformat() if inquiry and inquiry.updated_at else None,
            "inquiry_status": _get_inquiry_badge_status(inquiry),
        })
        total_boxes += box_count
        total_amount += amount

    return Response({
        "days": days,
        "total_boxes": total_boxes,
        "total_amount": total_amount,
    })


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_settlement_inquiry(request):
    crew = _get_crew_from_token(request)
    if not crew:
        return Response(
            {"detail": SESSION_EXPIRED_DETAIL},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    serializer = MobileSettlementInquiryRequestSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    target_date = serializer.validated_data["date"]

    inquiry = (
        SettlementInquiry.objects.filter(crew_member=crew, dispatch_date=target_date)
        .prefetch_related("messages")
        .first()
    )
    snapshot = _get_settlement_day_snapshot(crew, target_date)

    if not inquiry and not snapshot:
        return Response(
            {"detail": "해당 날짜의 정산 정보가 없습니다."},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(_build_mobile_inquiry_payload(inquiry, snapshot))


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_settlement_inquiry_comment(request):
    crew = _get_crew_from_token(request)
    if not crew:
        return Response(
            {"detail": SESSION_EXPIRED_DETAIL},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    serializer = MobileSettlementInquiryCommentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    target_date = serializer.validated_data["date"]
    content = serializer.validated_data["content"]

    snapshot = _get_settlement_day_snapshot(crew, target_date)
    inquiry = (
        SettlementInquiry.objects.filter(crew_member=crew, dispatch_date=target_date)
        .prefetch_related("messages")
        .first()
    )

    if not inquiry and not snapshot:
        return Response(
            {"detail": "해당 날짜의 정산 정보가 없습니다."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not inquiry:
        inquiry = SettlementInquiry.objects.create(
            crew_member=crew,
            crew_name=crew.name,
            team=crew.team,
            team_name=crew.team.name if crew.team else "",
            dispatch_date=target_date,
            original_boxes=snapshot["box_count"],
            original_pay_price=snapshot["pay_price"],
            original_adjustment=snapshot["adjustment_amount"],
            original_total=snapshot["total_amount"],
            boxes=snapshot["box_count"],
            pay_price=snapshot["pay_price"],
            is_overtime=snapshot["is_overtime"],
            adjustment_amount=snapshot["adjustment_amount"],
            total_amount=snapshot["total_amount"],
            status="OPEN",
            last_by="crew",
        )
        inquiry = SettlementInquiry.objects.prefetch_related("messages").get(pk=inquiry.pk)

    InquiryMessage.objects.create(
        inquiry=inquiry,
        author_type="crew",
        author_name=crew.name,
        content=content,
    )

    inquiry.last_by = "crew"
    inquiry.status = "OPEN"
    inquiry.save(update_fields=["last_by", "status", "updated_at"])
    inquiry.refresh_from_db()

    return Response(
        _build_mobile_inquiry_payload(inquiry, snapshot),
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_settlement_inquiry_read(request):
    crew = _get_crew_from_token(request)
    if not crew:
        return Response(
            {"detail": SESSION_EXPIRED_DETAIL},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    serializer = MobileSettlementInquiryReadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        inquiry = SettlementInquiry.objects.get(
            pk=serializer.validated_data["inquiry_id"],
            crew_member=crew,
        )
    except SettlementInquiry.DoesNotExist:
        return Response(
            {"detail": "문의 내역을 찾을 수 없습니다."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if inquiry.last_by == "admin" and inquiry.status == "ANSWERED":
        inquiry.status = "READ"
        inquiry.save(update_fields=["status", "updated_at"])

    return Response(
        {
            "id": inquiry.id,
            "status": inquiry.status,
            "badge_status": _get_inquiry_badge_status(inquiry),
        }
    )


# =============================================================================
# 愿由ъ옄???뱀씤 API (湲곗〈 ????쒕낫?쒖뿉???ъ슜)
# =============================================================================


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def admin_mobile_app_config(request):
    forbidden = _admin_required(request)
    if forbidden:
        return forbidden

    config = _get_mobile_app_message_config()

    if request.method == "GET":
        serializer = MobileAdminAppConfigSerializer(
            _serialize_mobile_app_config_payload(include_sections=True)
        )
        return Response(serializer.data)

    serializer = MobileAdminAppConfigWriteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    config.message_overrides = sanitize_mobile_app_message_overrides(
        serializer.validated_data.get("messages", {})
    )
    config.save(update_fields=["message_overrides", "updated_at"])

    response_serializer = MobileAdminAppConfigSerializer(
        _serialize_mobile_app_config_payload(include_sections=True)
    )
    return Response(response_serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_mobile_approvals(request):
    """紐⑤컮????媛???뱀씤? ???댁긽 ?ъ슜?섏? ?딆쑝誘濡?鍮?紐⑸줉??諛섑솚?쒕떎."""
    return Response([])


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def admin_mobile_approval_action(request, pk):
    """FR-604: ?뱀씤/嫄곗젅 泥섎━"""
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
    """FR-603: ?뱀씤 湲곗궗 紐⑸줉"""
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
    """???묎렐 鍮꾪솢?깊솕 (?뚰봽????젣)"""
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



