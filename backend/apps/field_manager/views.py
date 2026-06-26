"""현장관리자 앱 전용 API."""
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    parser_classes,
    permission_classes,
)
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
import jwt

from apps.vehicle_management.models import (
    Company, SubscriptionRequest, ReturnRequest, ReturnRequestPhoto, ASRequest, CalendarEvent,
)
from apps.vehicle_management.holiday_utils import holiday_dates_between
from .models import FieldManagerAccount, FieldManagerSession, normalize_phone
from .serializers import (
    FieldManagerLoginSerializer,
    FmSubscriptionRequestSerializer,
    FmReturnRequestSerializer,
    FmASRequestSerializer,
    FmBlockedDatesQuerySerializer,
    RETURN_PHOTO_FIELD_NAMES,
    validate_blocked_calendar_date,
)


FM_TOKEN_TTL_HOURS = 24


def _account_identity(account: FieldManagerAccount) -> dict:
    return {
        'account_id': account.id,
        'company_code': account.company.code,
        'team_code': account.team_code,
        'phone': account.phone,
        'display_phone': account.display_phone or account.phone,
        'name': account.name,
    }


def _issue_fm_token(account: FieldManagerAccount) -> str:
    payload = {
        'kind': 'field_manager',
        **_account_identity(account),
        'iat': int(timezone.now().timestamp()),
        'exp': int((timezone.now() + timedelta(hours=FM_TOKEN_TTL_HOURS)).timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def _decode_fm_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        if payload.get('kind') != 'field_manager':
            return None
        return payload
    except jwt.PyJWTError:
        return None


def _find_active_account(payload: dict) -> FieldManagerAccount | None:
    account_id = payload.get('account_id')
    qs = FieldManagerAccount.objects.select_related('company').filter(
        is_active=True,
        company__is_active=True,
    )
    if account_id:
        account = qs.filter(id=account_id).first()
        if account:
            return account

    company_code = str(payload.get('company_code') or '').strip().upper()
    team_code = str(payload.get('team_code') or '').strip().upper()
    phone = normalize_phone(payload.get('phone'))
    if not company_code or not team_code or not phone:
        return None
    return qs.filter(
        company__code=company_code,
        team_code=team_code,
        phone=phone,
    ).first()


def _auth_from_request(request) -> dict | None:
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        payload = _decode_fm_token(auth.removeprefix('Bearer ').strip())
        if not payload:
            return None
        account = _find_active_account(payload)
        if not account:
            return None
        return {
            **_account_identity(account),
            'account': account,
            'company': account.company,
        }
    return None


def _auth_required(request) -> dict | Response:
    auth = _auth_from_request(request)
    if not auth:
        return Response({'detail': '인증이 필요합니다. 다시 로그인해 주세요.'}, status=401)
    return auth


def _phone_variants(account: FieldManagerAccount) -> set[str]:
    phone = normalize_phone(account.phone)
    variants = {phone}
    if account.display_phone:
        variants.add(account.display_phone)
    if len(phone) == 10:
        variants.add(f'{phone[:3]}-{phone[3:6]}-{phone[6:]}')
    if len(phone) == 11:
        variants.add(f'{phone[:3]}-{phone[3:7]}-{phone[7:]}')
    return {value for value in variants if value}


# ── 1. Login ──────────────────────────────────────────────────────────────────
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def fm_login(request):
    s = FieldManagerLoginSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    d = s.validated_data
    company = Company.objects.filter(code=d['company_code'], is_active=True).first()
    if not company:
        return Response({'detail': '존재하지 않는 회사입니다.'}, status=400)

    account = FieldManagerAccount.objects.select_related('company').filter(
        company=company,
        team_code=d['team_code'],
        phone=d['phone'],
        is_active=True,
    ).first()
    if not account:
        return Response({'detail': '등록되지 않은 현장관리자입니다. 관리자에게 등록을 요청해 주세요.'}, status=403)

    account.last_login_at = timezone.now()
    account.save(update_fields=['last_login_at', 'updated_at'])
    FieldManagerSession.objects.create(
        account=account,
        company_code=account.company.code,
        team_code=account.team_code,
        phone=account.phone,
        user_agent=request.headers.get('User-Agent', '')[:255],
        ip_address=(request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
                    or request.META.get('REMOTE_ADDR')),
    )
    token = _issue_fm_token(account)
    return Response({
        'token': token,
        'token_type': 'Bearer',
        'expires_in_hours': FM_TOKEN_TTL_HOURS,
        'identity': _account_identity(account),
    })


# ── 2. 구독 요청 등록 (APP-04) ────────────────────────────────────────────────
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def fm_subscription_request(request):
    auth = _auth_required(request)
    if isinstance(auth, Response):
        return auth
    s = FmSubscriptionRequestSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    d = s.validated_data
    company = auth['company']
    account = auth['account']
    validate_blocked_calendar_date(company, d['requested_date'], 'requested_date')
    req = SubscriptionRequest.objects.create(
        company=company,
        team_code=account.team_code,
        phone=account.phone,
        requested_date=d['requested_date'],
        quantity=d['quantity'],
        status='REQUESTED',
    )
    CalendarEvent.objects.create(
        company=company, kind='REQ_HOPE',
        event_date=d['requested_date'],
        title=f'{account.team_code}조 요청 {d["quantity"]}대',
        body=f'전화: {account.display_phone or account.phone}',
        related_subscription=req,
    )
    return Response({'id': req.id, 'status': req.status}, status=201)


# ── 3. 구독 반납 등록 (APP-05) ────────────────────────────────────────────────
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def fm_return_request(request):
    auth = _auth_required(request)
    if isinstance(auth, Response):
        return auth
    s = FmReturnRequestSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    d = s.validated_data
    company = auth['company']
    account = auth['account']
    validate_blocked_calendar_date(company, d['hope_date'], 'hope_date')
    with transaction.atomic():
        req = ReturnRequest.objects.create(
            company=company,
            team_code=account.team_code,
            phone=account.phone,
            vehicle_number=d['vehicle_number'],
            reason=d['reason'],
            hope_date=d['hope_date'],
            hope_time=d['hope_time'],
            status='REQUESTED',
        )
        for field_name, kind in RETURN_PHOTO_FIELD_NAMES.items():
            ReturnRequestPhoto.objects.create(
                request=req,
                kind=kind,
                image=d[field_name],
            )
        CalendarEvent.objects.create(
            company=company, kind='RET_HOPE',
            event_date=d['hope_date'], event_time=d['hope_time'],
            title=f'{account.team_code}조 {d["vehicle_number"]} 반납 희망',
            body=d['reason'][:200],
            related_return=req,
        )
    return Response({'id': req.id, 'status': req.status}, status=201)


# ── 4. A/S 요청 등록 (APP-06) ─────────────────────────────────────────────────
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def fm_as_request(request):
    auth = _auth_required(request)
    if isinstance(auth, Response):
        return auth
    s = FmASRequestSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    d = s.validated_data
    company = auth['company']
    account = auth['account']
    req = ASRequest.objects.create(
        company=company,
        team_code=account.team_code,
        phone=account.phone,
        vehicle_number=d['vehicle_number'],
        owner_name=d['owner_name'],
        owner_phone=d['owner_phone'],
        reason=d['reason'],
        status='REQUESTED',
    )
    return Response({'id': req.id, 'status': req.status}, status=201)


# ── 5. 반납 불가일 조회 (APP-05 캘린더 disabled 처리용) ──────────────────────
@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def fm_blocked_dates(request):
    auth = _auth_required(request)
    if isinstance(auth, Response):
        return auth
    s = FmBlockedDatesQuerySerializer(data=request.query_params)
    s.is_valid(raise_exception=True)
    d = s.validated_data
    qs = CalendarEvent.objects.filter(
        Q(company=auth['company']) | Q(company__isnull=True),
        kind='BLOCK',
    )
    if d.get('date_from'): qs = qs.filter(event_date__gte=d['date_from'])
    if d.get('date_to'):   qs = qs.filter(event_date__lte=d['date_to'])
    dates = {e.event_date.isoformat() for e in qs}
    if d.get('date_from') and d.get('date_to'):
        dates |= holiday_dates_between(d['date_from'], d['date_to'])
    dates = sorted(dates)
    return Response({'blocked_dates': dates})


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def fm_request_history(request):
    auth = _auth_required(request)
    if isinstance(auth, Response):
        return auth
    account = auth['account']
    phone_values = _phone_variants(account)

    filters = {
        'company': auth['company'],
        'team_code': account.team_code,
        'phone__in': phone_values,
    }
    subscription_requests = SubscriptionRequest.objects.filter(**filters).order_by('-created_at')
    return_requests = ReturnRequest.objects.filter(**filters).prefetch_related('photos').order_by('-created_at')
    as_requests = ASRequest.objects.filter(**filters).order_by('-created_at')

    return Response({
        'subscription_requests': [
            {
                'id': item.id,
                'requested_date': item.requested_date.isoformat(),
                'quantity': item.quantity,
                'status': item.status,
                'status_display': item.get_status_display(),
                'reject_reason': item.reject_reason,
                'created_at': item.created_at.isoformat(),
                'updated_at': item.updated_at.isoformat(),
            }
            for item in subscription_requests
        ],
        'return_requests': [
            {
                'id': item.id,
                'vehicle_number': item.vehicle_number,
                'reason': item.reason,
                'hope_date': item.hope_date.isoformat(),
                'hope_time': item.hope_time.strftime('%H:%M'),
                'status': item.status,
                'status_display': item.get_status_display(),
                'block_reason': item.block_reason,
                'available_dates': item.available_dates,
                'confirmed_date': item.confirmed_date.isoformat() if item.confirmed_date else None,
                'confirmed_time': item.confirmed_time.strftime('%H:%M') if item.confirmed_time else None,
                'photo_count': item.photos.count(),
                'created_at': item.created_at.isoformat(),
                'updated_at': item.updated_at.isoformat(),
            }
            for item in return_requests
        ],
        'as_requests': [
            {
                'id': item.id,
                'vehicle_number': item.vehicle_number,
                'owner_name': item.owner_name,
                'owner_phone': item.owner_phone,
                'reason': item.reason,
                'status': item.status,
                'status_display': item.get_status_display(),
                'admin_comment': item.admin_comment,
                'created_at': item.created_at.isoformat(),
                'updated_at': item.updated_at.isoformat(),
            }
            for item in as_requests
        ],
    })
