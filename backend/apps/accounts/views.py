from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from django.shortcuts import get_object_or_404
import logging

from .models import CompanyApp, DEFAULT_COMPANY_TABS, DEFAULT_SHIPPER_CODES, Shipper, User, Team, new_company_signup_token
from .serializers import (
    CompanyAppSerializer,
    CompanyAppSignupSerializer,
    CompanyAppUpdateSerializer,
    CompanyUserSignupSerializer,
    ShipperSerializer,
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    UserMeSerializer, TeamSerializer, CustomTokenObtainPairSerializer
)
from apps.common.company_scope import (
    filter_queryset_by_company_app,
    get_company_app_from_request,
)
from apps.dispatch.settlement_services import rebuild_team_settlements
from apps.mobile.models import LegalConsentHistory, record_legal_consent_history

logger = logging.getLogger(__name__)


def _clever_admin_usernames():
    names = set(getattr(settings, "CLEVER_ADMIN_USERNAMES", ["clever_admin"]))
    names.add("admin2")
    return names


def is_clever_admin_user(user):
    return bool(user and user.is_authenticated and user.username in _clever_admin_usernames())


class IsCleverAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return is_clever_admin_user(request.user)


def _company_signup_agreements():
    try:
        from apps.mobile.models import MobileAppMessageConfig

        messages = MobileAppMessageConfig.get_solo().merged_messages
    except Exception:
        messages = {}

    def message(key, default):
        return messages.get(key) or default

    return [
        {
            "key": "agree_terms",
            "required": True,
            "label": message("signup_web_terms_agreement_label", "[필수] CLEVER 관리자 회원 서비스 이용약관 동의"),
            "url": message("signup_web_terms_url", "/terms/"),
        },
        {
            "key": "agree_privacy_policy",
            "required": True,
            "label": message("signup_privacy_agreement_label", "[필수] 개인정보 처리방침 동의"),
            "url": message("signup_web_privacy_policy_url", "/privacy/"),
        },
        {
            "key": "agree_location_terms",
            "required": True,
            "label": message("signup_location_terms_agreement_label", "[필수] 위치기반서비스 이용약관 동의"),
            "url": message("signup_web_location_terms_url", "/location-terms/"),
        },
        {
            "key": "agree_data_processing",
            "required": True,
            "label": message(
                "signup_data_processing_agreement_label",
                "[필수] 제3자 정보제공 동의",
            ),
            "url": message("signup_web_data_processing_url", "/data-processing/"),
        },
        {
            "key": "agree_marketing",
            "required": False,
            "label": message("signup_marketing_agreement_label", "[선택] 마케팅 및 이벤트 정보 수신 동의"),
            "url": message("signup_web_marketing_url", "/marketing-consent/"),
        },
    ]


def _company_app_public_payload(company):
    return {
        "id": company.id,
        "code": company.code,
        "name": company.name,
        "status": company.status,
        "enabled_tabs": company.enabled_tabs or [],
        "enabled_shippers": company.enabled_shippers or ["kurly"],
        "enabled_shipper_tabs": company.enabled_shipper_tabs or {},
    }


def _can_approve_company_user(request_user, company):
    if not request_user or not request_user.is_authenticated:
        return False
    if is_clever_admin_user(request_user):
        return True
    if company.representative_user_id and company.representative_user_id == request_user.id:
        return True
    return bool(
        not company.representative_user_id
        and request_user.is_admin()
        and getattr(request_user, "company_app", "") == company.code
    )


def _pending_company_user_queryset(company):
    queryset = User.objects.filter(
        company_app=company.code,
        role="ADMIN",
        is_active=False,
    ).order_by("-date_joined", "-id")
    if company.representative_user_id:
        queryset = queryset.exclude(pk=company.representative_user_id)
    return queryset


def _pending_company_user_payload(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "company_app": user.company_app,
        "created_at": user.date_joined,
    }


class ShipperViewSet(viewsets.ModelViewSet):
    queryset = Shipper.objects.all()
    serializer_class = ShipperSerializer
    permission_classes = [permissions.IsAuthenticated, IsCleverAdmin]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsCleverAdmin()]

    def get_queryset(self):
        return Shipper.objects.all().order_by("sort_order", "name", "code")

    def destroy(self, request, *args, **kwargs):
        shipper = self.get_object()
        shipper_code = shipper.code
        if shipper_code in DEFAULT_SHIPPER_CODES:
            return Response(
                {"detail": "기본 화주사는 삭제할 수 없습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            for company in CompanyApp.objects.all():
                enabled = list(company.enabled_shippers or [])
                if shipper_code not in enabled:
                    continue
                next_enabled = [code for code in enabled if code != shipper_code]
                company.enabled_shippers = next_enabled or list(DEFAULT_SHIPPER_CODES)
                next_shipper_tabs = dict(company.enabled_shipper_tabs or {})
                next_shipper_tabs.pop(shipper_code, None)
                company.enabled_shipper_tabs = next_shipper_tabs
                next_tabs = []
                for tabs in next_shipper_tabs.values():
                    for tab in tabs or []:
                        if tab not in next_tabs:
                            next_tabs.append(tab)
                company.enabled_tabs = next_tabs or list(DEFAULT_COMPANY_TABS)
                company.save(update_fields=["enabled_shippers", "enabled_shipper_tabs", "enabled_tabs", "updated_at"])
            shipper.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CustomTokenObtainPairView(TokenObtainPairView):
    """JWT 토큰 발급"""
    serializer_class = CustomTokenObtainPairSerializer


class CompanyAppViewSet(viewsets.ModelViewSet):
    queryset = CompanyApp.objects.all()
    serializer_class = CompanyAppSerializer
    permission_classes = [permissions.IsAuthenticated, IsCleverAdmin]

    def get_queryset(self):
        return CompanyApp.objects.all().order_by("name", "code")

    def get_serializer_class(self):
        if self.action in ("partial_update", "update"):
            return CompanyAppUpdateSerializer
        return CompanyAppSerializer

    def perform_create(self, serializer):
        save_kwargs = {"created_by": self.request.user}
        if serializer.validated_data.get("enabled_tabs"):
            save_kwargs["enabled_tabs"] = serializer.validated_data["enabled_tabs"]
        if serializer.validated_data.get("enabled_shippers"):
            save_kwargs["enabled_shippers"] = serializer.validated_data["enabled_shippers"]
        serializer.save(**save_kwargs)

    def destroy(self, request, *args, **kwargs):
        company = self.get_object()
        if company.is_core_company:
            return Response(
                {"detail": "기본 회사는 삭제할 수 없습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        now = timezone.now()
        company.status = CompanyApp.Status.DELETED
        company.deleted_at = now
        company.delete_retention_until = now + timedelta(days=30)
        company.deleted_by = request.user
        company.save(
            update_fields=[
                "status",
                "deleted_at",
                "delete_retention_until",
                "deleted_by",
                "updated_at",
            ]
        )
        return Response(self.get_serializer(company).data)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        company = self.get_object()
        if company.status != CompanyApp.Status.DELETED:
            return Response({"detail": "삭제된 회사만 복구할 수 있습니다."}, status=status.HTTP_400_BAD_REQUEST)
        company.status = CompanyApp.Status.ACTIVE
        company.deleted_at = None
        company.delete_retention_until = None
        company.deleted_by = None
        company.restored_at = timezone.now()
        company.restored_by = request.user
        company.save(
            update_fields=[
                "status",
                "deleted_at",
                "delete_retention_until",
                "deleted_by",
                "restored_at",
                "restored_by",
                "updated_at",
            ]
        )
        return Response(self.get_serializer(company).data)

    @action(detail=True, methods=["delete"], url_path="permanent-delete")
    @transaction.atomic
    def permanent_delete(self, request, pk=None):
        company = self.get_object()
        if company.is_core_company:
            return Response(
                {"detail": "기본 회사는 완전삭제할 수 없습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if company.status != CompanyApp.Status.DELETED:
            return Response(
                {"detail": "삭제 보관 상태의 회사만 완전삭제할 수 있습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        company_code = company.code
        User.objects.filter(company_app=company_code).update(is_active=False)
        company.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        company = self.get_object()
        if company.representative_user:
            company.representative_user.is_active = True
            company.representative_user.save(update_fields=["is_active"])
        company.status = CompanyApp.Status.ACTIVE
        company.approved_at = timezone.now()
        company.approved_by = request.user
        company.rejected_at = None
        company.rejected_by = None
        company.deleted_at = None
        company.delete_retention_until = None
        company.save(
            update_fields=[
                "status",
                "approved_at",
                "approved_by",
                "rejected_at",
                "rejected_by",
                "deleted_at",
                "delete_retention_until",
                "updated_at",
            ]
        )
        return Response(self.get_serializer(company).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        company = self.get_object()
        if company.representative_user:
            company.representative_user.is_active = False
            company.representative_user.save(update_fields=["is_active"])
        company.status = CompanyApp.Status.REJECTED
        company.rejected_at = timezone.now()
        company.rejected_by = request.user
        company.save(update_fields=["status", "rejected_at", "rejected_by", "updated_at"])
        return Response(self.get_serializer(company).data)

    @action(detail=True, methods=["post"], url_path="rotate-signup-token")
    def rotate_signup_token(self, request, pk=None):
        company = self.get_object()
        company.signup_token = new_company_signup_token()
        company.save(update_fields=["signup_token", "updated_at"])
        return Response(self.get_serializer(company).data)

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny])
    def public(self, request):
        queryset = CompanyApp.objects.filter(
            status=CompanyApp.Status.ACTIVE,
            deleted_at__isnull=True,
        ).order_by("name", "code")
        return Response([_company_app_public_payload(company) for company in queryset])


class CompanyAppSignupView(APIView):
    permission_classes = [permissions.AllowAny]

    def get_company(self, token):
        return get_object_or_404(CompanyApp, signup_token=token)

    def get(self, request, token):
        company = self.get_company(token)
        if company.status == CompanyApp.Status.DELETED:
            return Response({"detail": "삭제된 회사 초대 링크입니다."}, status=status.HTTP_410_GONE)
        return Response(
            {
                "company": CompanyAppSerializer(company, context={"request": request}).data,
                "agreements": _company_signup_agreements(),
            }
        )

    @transaction.atomic
    def post(self, request, token):
        company = self.get_company(token)
        if company.status == CompanyApp.Status.DELETED:
            return Response({"detail": "삭제된 회사 초대 링크입니다."}, status=status.HTTP_410_GONE)
        if company.status == CompanyApp.Status.ACTIVE:
            return Response({"detail": "이미 승인된 회사입니다."}, status=status.HTTP_400_BAD_REQUEST)
        if company.representative_user and company.status == CompanyApp.Status.PENDING_APPROVAL:
            return Response({"detail": "이미 승인 대기 중인 신청입니다."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CompanyAppSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        now = timezone.now()

        user = User.objects.create_user(
            username=data["username"],
            email=f"{data['username']}@{company.code}.company.local",
            password=data["password"],
            first_name=data["company_name"],
            role="ADMIN",
            company_app=company.code,
            is_active=False,
        )

        company.name = data["company_name"]
        company.representative_user = user
        company.status = CompanyApp.Status.PENDING_APPROVAL
        company.signup_submitted_at = now
        company.terms_agreed_at = now
        company.privacy_policy_agreed_at = now
        company.location_terms_agreed_at = now
        company.data_processing_agreed_at = now
        if data.get("agree_marketing"):
            company.marketing_agreed_at = now
        company.save(
            update_fields=[
                "name",
                "representative_user",
                "status",
                "signup_submitted_at",
                "terms_agreed_at",
                "privacy_policy_agreed_at",
                "location_terms_agreed_at",
                "data_processing_agreed_at",
                "marketing_agreed_at",
                "updated_at",
            ]
        )
        subject_identifier = f"{company.code}/{user.username}"
        consent_rows = [
            ("agree_terms", "web_terms", True),
            ("agree_privacy_policy", "privacy_policy", True),
            ("agree_location_terms", "location_terms", True),
            ("agree_data_processing", "data_processing", True),
            ("agree_marketing", "marketing_consent", bool(data.get("agree_marketing"))),
        ]
        for agreement_key, document_key, agreed in consent_rows:
            record_legal_consent_history(
                subject_type=LegalConsentHistory.SubjectType.COMPANY_APP,
                subject_identifier=subject_identifier,
                company_app=company,
                agreement_key=agreement_key,
                document_key=document_key,
                agreed=agreed,
                agreed_at=now,
                request=request,
            )
        return Response(
            {
                "detail": "회사 계정 신청이 완료되었습니다. CLEVER 관리자의 승인 후 로그인할 수 있습니다.",
                "company": CompanyAppSerializer(company, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class CompanyAppPublicDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, code):
        company = get_object_or_404(
            CompanyApp,
            code=str(code or "").strip().lower(),
            status=CompanyApp.Status.ACTIVE,
            deleted_at__isnull=True,
        )
        return Response(_company_app_public_payload(company))


class CompanyUserSignupView(APIView):
    permission_classes = [permissions.AllowAny]

    def get_company(self, code):
        return get_object_or_404(
            CompanyApp,
            code=str(code or "").strip().lower(),
            status=CompanyApp.Status.ACTIVE,
            deleted_at__isnull=True,
        )

    def get(self, request, code):
        company = self.get_company(code)
        return Response(
            {
                "company": _company_app_public_payload(company),
                "agreements": _company_signup_agreements(),
            }
        )

    @transaction.atomic
    def post(self, request, code):
        company = self.get_company(code)
        serializer = CompanyUserSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        now = timezone.now()

        user = User.objects.create_user(
            username=data["username"],
            email=f"{data['username']}@{company.code}.company.local",
            password=data["password"],
            role="ADMIN",
            company_app=company.code,
            is_active=False,
        )

        subject_identifier = f"{company.code}/{user.username}"
        consent_rows = [
            ("agree_terms", "web_terms", True),
            ("agree_privacy_policy", "privacy_policy", True),
            ("agree_location_terms", "location_terms", True),
            ("agree_data_processing", "data_processing", True),
            ("agree_marketing", "marketing_consent", bool(data.get("agree_marketing"))),
        ]
        for agreement_key, document_key, agreed in consent_rows:
            record_legal_consent_history(
                subject_type=LegalConsentHistory.SubjectType.COMPANY_APP,
                subject_identifier=subject_identifier,
                company_app=company,
                agreement_key=agreement_key,
                document_key=document_key,
                agreed=agreed,
                agreed_at=now,
                request=request,
            )

        return Response(
            {
                "detail": "회원가입 신청이 완료되었습니다. 대표자 승인 후 로그인할 수 있습니다.",
                "user": _pending_company_user_payload(user),
            },
            status=status.HTTP_201_CREATED,
        )


class CompanyUserSignupRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_company(self, request):
        company_code = get_company_app_from_request(request)
        return get_object_or_404(
            CompanyApp,
            code=company_code,
            status=CompanyApp.Status.ACTIVE,
            deleted_at__isnull=True,
        )

    def get(self, request):
        company = self.get_company(request)
        if not _can_approve_company_user(request.user, company):
            return Response({"detail": "대표자 계정만 회원가입 신청을 승인할 수 있습니다."}, status=status.HTTP_403_FORBIDDEN)

        items = [_pending_company_user_payload(user) for user in _pending_company_user_queryset(company)]
        return Response({"count": len(items), "items": items})

    def post(self, request, pk, action):
        company = self.get_company(request)
        if not _can_approve_company_user(request.user, company):
            return Response({"detail": "대표자 계정만 회원가입 신청을 처리할 수 있습니다."}, status=status.HTTP_403_FORBIDDEN)

        target = get_object_or_404(_pending_company_user_queryset(company), pk=pk)
        if action == "approve":
            target.is_active = True
            target.save(update_fields=["is_active"])
            return Response({"detail": "회원가입 신청을 승인했습니다.", "user": _pending_company_user_payload(target)})
        if action == "reject":
            payload = _pending_company_user_payload(target)
            target.delete()
            return Response({"detail": "회원가입 신청을 거절했습니다.", "user": payload})
        return Response({"detail": "지원하지 않는 처리입니다."}, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    """사용자 관리"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        """액션에 따른 serializer 선택"""
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        elif self.action == 'me':
            return UserMeSerializer
        return UserSerializer

    def get_queryset(self):
        """사용자 권한에 따른 queryset 필터링"""
        user = self.request.user

        # 관리자는 모든 사용자 조회
        if user.is_admin():
            if is_clever_admin_user(user):
                return User.objects.all()
            return User.objects.filter(company_app=getattr(user, "company_app", "cheonha"))

        # 팀장은 자신의 팀 멤버만 조회
        if user.is_team_leader():
            return User.objects.filter(team=user.team)

        # 일반 사용자는 자신의 정보만 조회
        return User.objects.filter(id=user.id)

    def create(self, request, *args, **kwargs):
        """사용자 생성"""
        # 관리자만 사용자 생성 가능
        if not request.user.is_admin():
            return Response(
                {'detail': '관리자만 사용자를 생성할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        save_kwargs = {}
        if not is_clever_admin_user(request.user):
            save_kwargs["company_app"] = getattr(request.user, "company_app", "cheonha")
        serializer.save(**save_kwargs)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        """사용자 생성 시 생성자 정보 기록"""
        serializer.save()
        logger.info(f'사용자 생성: {serializer.instance.username} (생성자: {self.request.user.username})')

    def perform_update(self, serializer):
        """사용자 수정 시 수정자 정보 기록"""
        serializer.save()
        logger.info(f'사용자 수정: {serializer.instance.username} (수정자: {self.request.user.username})')

    @action(detail=False, methods=['get'])
    def me(self, request):
        """현재 사용자 정보 조회"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """비밀번호 변경"""
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        new_password_confirm = request.data.get('new_password_confirm')

        # 기존 비밀번호 확인
        if not user.check_password(old_password):
            return Response(
                {'old_password': ['기존 비밀번호가 일치하지 않습니다.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 새 비밀번호 일치 확인
        if new_password != new_password_confirm:
            return Response(
                {'new_password': ['새 비밀번호가 일치하지 않습니다.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 비밀번호 변경
        user.set_password(new_password)
        user.save()

        logger.info(f'비밀번호 변경: {user.username}')

        return Response(
            {'detail': '비밀번호가 변경되었습니다.'},
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'])
    def logout(self, request):
        """로그아웃"""
        # 간단한 로그아웃 처리 (JWT 토큰 블랙리스트는 settings에서 BLACKLIST_AFTER_ROTATION 설정)
        logger.info(f'로그아웃: {request.user.username}')
        return Response({'detail': '로그아웃되었습니다.'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def roles(self, request):
        """역할 목록 조회"""
        roles = [{'code': code, 'name': name} for code, name in User.ROLE_CHOICES]
        return Response(roles)


class TeamViewSet(viewsets.ModelViewSet):
    """팀 관리"""
    queryset = Team.objects.all()
    serializer_class = TeamSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        queryset = filter_queryset_by_company_app(Team.objects.filter(is_active=True), self.request)
        shipper_code = str(self.request.query_params.get("shipper_code") or "").strip().lower()
        if shipper_code:
            queryset = queryset.filter(shipper_code=shipper_code)
        return queryset

    def create(self, request, *args, **kwargs):
        """팀 생성"""
        # 관리자만 팀 생성 가능
        if not request.user.is_admin():
            return Response(
                {'detail': '관리자만 팀을 생성할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            company_app=get_company_app_from_request(request),
            shipper_code=serializer.validated_data.get("shipper_code") or "kurly",
        )

        logger.info(f'팀 생성: {serializer.instance.name} (생성자: {request.user.username})')

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='shipper-team')
    def create_shipper_team(self, request):
        if not request.user.is_admin():
            return Response(
                {'detail': '관리자만 조를 생성할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        company_app = get_company_app_from_request(request)
        shipper_code = str(request.data.get('shipper_code') or 'kurly').strip().lower()
        name = str(request.data.get('name') or '').strip()
        if not name:
            return Response({'detail': '조 이름을 입력해 주세요.'}, status=status.HTTP_400_BAD_REQUEST)
        if Team.objects.filter(company_app=company_app, shipper_code=shipper_code, name=name, is_active=True).exists():
            return Response({'detail': '이미 같은 화주사에 등록된 조 이름입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        prefix = ''.join(ch for ch in shipper_code.upper() if ch.isalnum())[:2] or 'T'
        for index in range(1, 1000):
            code = f'{prefix}{index:03d}'[:10]
            if not Team.objects.filter(company_app=company_app, code=code).exists():
                team = Team.objects.create(
                    company_app=company_app,
                    shipper_code=shipper_code,
                    code=code,
                    name=name,
                    is_active=True,
                )
                return Response(self.get_serializer(team).data, status=status.HTTP_201_CREATED)
        return Response({'detail': '사용 가능한 조 코드를 만들 수 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

    def perform_update(self, serializer):
        """팀 수정 시 수정자 정보 기록"""
        serializer.save()
        logger.info(f'팀 수정: {serializer.instance.name} (수정자: {self.request.user.username})')

    @action(detail=True, methods=['post'])
    def recalc_settlements(self, request, pk=None):
        """팀 단가 변경 후 기존 정산 재계산"""
        team = self.get_object()
        result = rebuild_team_settlements(team)
        return Response({
            'detail': (
                f"{team.name} 정산 재계산 완료 "
                f"(그룹 {result['rebuilt_groups']}건, 정산 {result['settlement_count']}건, 업로드 {result['upload_count']}건)"
            ),
            **result,
        })

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def teams_list(self, request):
        """팀 목록 조회 (권한 없이 조회 가능)"""
        teams = filter_queryset_by_company_app(Team.objects.filter(is_active=True), request)
        shipper_code = str(request.query_params.get("shipper_code") or "").strip().lower()
        if shipper_code:
            teams = teams.filter(shipper_code=shipper_code)
        serializer = self.get_serializer(teams, many=True)
        return Response(serializer.data)
