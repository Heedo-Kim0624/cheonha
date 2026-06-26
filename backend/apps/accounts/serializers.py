from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import (
    ALL_COMPANY_TABS,
    DEFAULT_COMPANY_TABS,
    DEFAULT_SHIPPER_CODES,
    CompanyApp,
    CompanyTenant,
    Shipper,
    Team,
    User,
)


def normalize_company_tabs(value):
    requested = list(value or [])
    cleaned = []
    for tab in DEFAULT_COMPANY_TABS + requested:
        if tab in ALL_COMPANY_TABS and tab not in cleaned:
            cleaned.append(tab)
    return cleaned


def normalize_shipper_tabs(value):
    requested = list(value or [])
    cleaned = []
    for tab in requested:
        if tab in ALL_COMPANY_TABS and tab not in cleaned:
            cleaned.append(tab)
    return cleaned


def normalize_company_shippers(value):
    requested = [str(item or "").strip().lower() for item in list(value or [])]
    cleaned = []
    for code in requested or DEFAULT_SHIPPER_CODES:
        if code and code not in cleaned:
            cleaned.append(code)
    return cleaned


def normalize_enabled_shipper_tabs(enabled_shippers, shipper_tabs=None, fallback_tabs=None):
    codes = normalize_company_shippers(enabled_shippers)
    raw_map = shipper_tabs if isinstance(shipper_tabs, dict) else {}
    fallback = normalize_company_tabs(fallback_tabs or [])
    shipper_rows = {
        shipper.code: shipper
        for shipper in Shipper.objects.filter(code__in=codes)
    }

    normalized = {}
    for code in codes:
        shipper = shipper_rows.get(code)
        available = normalize_shipper_tabs(getattr(shipper, "available_tabs", None) or ALL_COMPANY_TABS)
        configured = raw_map.get(code)
        if configured is None:
            configured = getattr(shipper, "default_enabled_tabs", None) or fallback
        configured_tabs = normalize_shipper_tabs(configured)
        if available:
            configured_tabs = [tab for tab in configured_tabs if tab in available]
        if not configured_tabs:
            configured_tabs = ["settlement"] if code == "one" else normalize_shipper_tabs(DEFAULT_COMPANY_TABS)
            if available:
                configured_tabs = [tab for tab in configured_tabs if tab in available]
        normalized[code] = configured_tabs
    return normalized


def union_shipper_tabs(enabled_shipper_tabs):
    tabs = []
    for tab_list in (enabled_shipper_tabs or {}).values():
        for tab in normalize_shipper_tabs(tab_list):
            if tab not in tabs:
                tabs.append(tab)
    return tabs


class ShipperSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipper
        fields = [
            "id",
            "code",
            "name",
            "status",
            "upload_type",
            "upload_profile",
            "operation_report_profile",
            "settlement_profile",
            "default_enabled_tabs",
            "available_tabs",
            "sort_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_code(self, value):
        value = str(value or "").strip().lower()
        if not value:
            raise serializers.ValidationError("화주사 코드를 입력해 주세요.")
        if not value.replace("-", "").replace("_", "").isalnum():
            raise serializers.ValidationError("화주사 코드는 영문, 숫자, -, _만 사용할 수 있습니다.")
        return value


class CompanyAppSerializer(serializers.ModelSerializer):
    representative_username = serializers.CharField(
        source="representative_user.username",
        read_only=True,
    )
    signup_url = serializers.SerializerMethodField()
    is_core_company = serializers.BooleanField(read_only=True)
    shipper_names = serializers.SerializerMethodField()
    tenant_schema_name = serializers.CharField(source="tenant.schema_name", read_only=True, default="")
    tenant_status = serializers.CharField(source="tenant.status", read_only=True, default="")
    tenant_routing_enabled = serializers.BooleanField(
        source="tenant.routing_enabled",
        read_only=True,
        default=False,
    )

    class Meta:
        model = CompanyApp
        fields = [
            "id",
            "code",
            "name",
            "status",
            "enabled_tabs",
            "enabled_shippers",
            "enabled_shipper_tabs",
            "shipper_names",
            "signup_token",
            "signup_url",
            "representative_user",
            "representative_username",
            "signup_submitted_at",
            "approved_at",
            "rejected_at",
            "deleted_at",
            "delete_retention_until",
            "is_core_company",
            "tenant_schema_name",
            "tenant_status",
            "tenant_routing_enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "signup_token",
            "representative_user",
            "signup_submitted_at",
            "approved_at",
            "rejected_at",
            "deleted_at",
            "delete_retention_until",
            "created_at",
            "updated_at",
        ]

    def get_signup_url(self, obj):
        request = self.context.get("request")
        path = f"/company-signup/{obj.signup_token}"
        if request:
            return request.build_absolute_uri(path)
        return path

    def get_shipper_names(self, obj):
        codes = normalize_company_shippers(getattr(obj, "enabled_shippers", []))
        shippers = {
            shipper.code: shipper.name
            for shipper in Shipper.objects.filter(code__in=codes)
        }
        return [shippers.get(code, code.upper()) for code in codes]

    def validate_code(self, value):
        value = str(value or "").strip().lower()
        if not value:
            raise serializers.ValidationError("회사 코드를 입력해 주세요.")
        if not value.replace("-", "").replace("_", "").isalnum():
            raise serializers.ValidationError("회사 코드는 영문, 숫자, -, _ 만 사용할 수 있습니다.")
        if not self.instance and (
            Team.objects.filter(company_app=value).exists()
            or User.objects.filter(company_app=value).exists()
        ):
            raise serializers.ValidationError(
                "기존 데이터가 남아 있는 회사 코드입니다. 다른 코드를 사용해 주세요."
            )
        return value

    def validate_enabled_tabs(self, value):
        return normalize_company_tabs(value)

    def validate_enabled_shippers(self, value):
        cleaned = normalize_company_shippers(value)
        existing = set(Shipper.objects.filter(code__in=cleaned).values_list("code", flat=True))
        missing = [code for code in cleaned if code not in existing]
        if missing:
            raise serializers.ValidationError(f"등록되지 않은 화주사입니다: {', '.join(missing)}")
        return cleaned

    def validate_enabled_shipper_tabs(self, value):
        if value in (None, ""):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("화주사별 탭 구성은 객체 형태여야 합니다.")
        return value

    def validate(self, attrs):
        enabled_shippers = attrs.get(
            "enabled_shippers",
            getattr(self.instance, "enabled_shippers", DEFAULT_SHIPPER_CODES),
        )
        fallback_tabs = attrs.get(
            "enabled_tabs",
            getattr(self.instance, "enabled_tabs", DEFAULT_COMPANY_TABS),
        )
        shipper_tabs = attrs.get(
            "enabled_shipper_tabs",
            getattr(self.instance, "enabled_shipper_tabs", {}) or {},
        )
        normalized_map = normalize_enabled_shipper_tabs(
            enabled_shippers,
            shipper_tabs,
            fallback_tabs=fallback_tabs,
        )
        attrs["enabled_shipper_tabs"] = normalized_map
        attrs["enabled_tabs"] = union_shipper_tabs(normalized_map) or normalize_company_tabs(fallback_tabs)
        return attrs


class CompanyTenantSerializer(serializers.ModelSerializer):
    company_code = serializers.CharField(source="company_app.code", read_only=True)
    company_name = serializers.CharField(source="company_app.name", read_only=True)

    class Meta:
        model = CompanyTenant
        fields = [
            "id",
            "company_app",
            "company_code",
            "company_name",
            "schema_name",
            "status",
            "routing_enabled",
            "last_migrated_at",
            "last_verified_at",
            "last_error",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "created_at",
            "updated_at",
        ]


class CompanyAppUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyApp
        fields = ["name", "enabled_tabs", "enabled_shippers", "enabled_shipper_tabs"]

    def validate_enabled_tabs(self, value):
        return normalize_company_tabs(value)

    def validate_enabled_shippers(self, value):
        cleaned = normalize_company_shippers(value)
        existing = set(Shipper.objects.filter(code__in=cleaned).values_list("code", flat=True))
        missing = [code for code in cleaned if code not in existing]
        if missing:
            raise serializers.ValidationError(f"등록되지 않은 화주사입니다: {', '.join(missing)}")
        return cleaned

    def validate_enabled_shipper_tabs(self, value):
        if value in (None, ""):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("화주사별 탭 구성은 객체 형태여야 합니다.")
        return value

    def validate(self, attrs):
        enabled_shippers = attrs.get(
            "enabled_shippers",
            getattr(self.instance, "enabled_shippers", DEFAULT_SHIPPER_CODES),
        )
        fallback_tabs = attrs.get(
            "enabled_tabs",
            getattr(self.instance, "enabled_tabs", DEFAULT_COMPANY_TABS),
        )
        shipper_tabs = attrs.get(
            "enabled_shipper_tabs",
            getattr(self.instance, "enabled_shipper_tabs", {}) or {},
        )
        normalized_map = normalize_enabled_shipper_tabs(
            enabled_shippers,
            shipper_tabs,
            fallback_tabs=fallback_tabs,
        )
        attrs["enabled_shipper_tabs"] = normalized_map
        attrs["enabled_tabs"] = union_shipper_tabs(normalized_map) or normalize_company_tabs(fallback_tabs)
        return attrs


class CompanyAppSignupSerializer(serializers.Serializer):
    company_name = serializers.CharField(max_length=100)
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    agree_terms = serializers.BooleanField()
    agree_privacy_policy = serializers.BooleanField()
    agree_location_terms = serializers.BooleanField()
    agree_data_processing = serializers.BooleanField()
    agree_marketing = serializers.BooleanField(required=False, default=False)

    def validate_username(self, value):
        value = str(value or "").strip()
        if not value:
            raise serializers.ValidationError("아이디를 입력해 주세요.")
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("이미 사용 중인 아이디입니다.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm", None):
            raise serializers.ValidationError({"password": "비밀번호가 일치하지 않습니다."})
        for key in (
            "agree_terms",
            "agree_privacy_policy",
            "agree_location_terms",
            "agree_data_processing",
        ):
            if not attrs.get(key):
                raise serializers.ValidationError({key: "필수 약관 동의가 필요합니다."})
        return attrs


class CompanyUserSignupSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    agree_terms = serializers.BooleanField()
    agree_privacy_policy = serializers.BooleanField()
    agree_location_terms = serializers.BooleanField()
    agree_data_processing = serializers.BooleanField()
    agree_marketing = serializers.BooleanField(required=False, default=False)

    def validate_username(self, value):
        value = str(value or "").strip()
        if not value:
            raise serializers.ValidationError("아이디를 입력해 주세요.")
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("이미 사용 중인 아이디입니다.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm", None):
            raise serializers.ValidationError({"password": "비밀번호가 일치하지 않습니다."})
        for key in (
            "agree_terms",
            "agree_privacy_policy",
            "agree_location_terms",
            "agree_data_processing",
        ):
            if not attrs.get(key):
                raise serializers.ValidationError({key: "필수 약관 동의가 필요합니다."})
        return attrs


class TeamSerializer(serializers.ModelSerializer):
    current_yongcha_pay_price = serializers.SerializerMethodField()
    has_mixed_yongcha_pay_price = serializers.SerializerMethodField()

    def get_current_yongcha_pay_price(self, obj):
        return int(obj.yongcha_pay_price or 3000)

    def get_has_mixed_yongcha_pay_price(self, obj):
        return False

    class Meta:
        model = Team
        fields = [
            "id",
            "code",
            "name",
            "company_app",
            "shipper_code",
            "leader",
            "receive_price",
            "pay_price",
            "default_overtime_cost",
            "yongcha_pay_price",
            "round_1_yongcha_pay_price",
            "round_2_yongcha_pay_price",
            "round_3_yongcha_pay_price",
            "yongcha_round_1_pay_price",
            "yongcha_round_2_pay_price",
            "yongcha_round_3_pay_price",
            "current_yongcha_pay_price",
            "has_mixed_yongcha_pay_price",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class UserSerializer(serializers.ModelSerializer):
    team_detail = TeamSerializer(source="team", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "company_app",
            "team",
            "team_detail",
            "phone",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
        extra_kwargs = {
            "password": {"write_only": True},
        }


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
            "role",
            "company_app",
            "team",
            "phone",
        ]

    def validate(self, data):
        password = data.get("password")
        password_confirm = data.pop("password_confirm", None)

        if password != password_confirm:
            raise serializers.ValidationError({"password": "비밀번호가 일치하지 않습니다."})

        return data

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "role",
            "company_app",
            "team",
            "phone",
            "is_active",
        ]


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT 토큰 생성 시 사용자 정보를 함께 넣는다."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.username
        token["email"] = user.email
        token["role"] = user.role
        token["company_app"] = getattr(user, "company_app", None)
        token["team_code"] = user.team.code if user.team else None
        return token

    def validate(self, attrs):
        authenticate_kwargs = {
            self.username_field: attrs[self.username_field],
            "password": attrs["password"],
        }
        try:
            authenticate_user = authenticate(**authenticate_kwargs)
        except TypeError as exc:
            msg = _("Unable to log in with provided credentials.")
            raise serializers.ValidationError(msg, code="authentication") from exc

        if authenticate_user is None or not authenticate_user.is_active:
            raise serializers.ValidationError(
                {
                    "detail": "사용자 인증에 실패했습니다. 사용자명 또는 비밀번호를 확인하세요."
                },
                code="authentication",
            )

        refresh = self.get_token(authenticate_user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}


class UserMeSerializer(serializers.ModelSerializer):
    team_detail = TeamSerializer(source="team", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "company_app",
            "team",
            "team_detail",
            "phone",
            "is_active",
        ]
