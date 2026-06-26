import re
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from .models import CrewMember, OvertimeSetting, YongchaPayGroup


_APP_VERSION_CODE_RE = re.compile(r"\((\d+)\)\s*$")
_APP_VERSION_TOKEN_RE = re.compile(r"(?:versionCode|vc|vcode)[\s:_-]*(\d+)", re.IGNORECASE)


def _positive_decimal(value):
    amount = Decimal(str(value or 0))
    return amount if amount > 0 else Decimal("0")


def parse_app_version_code(value):
    value = str(value or "").strip()
    if not value:
        return 0
    if value.isdigit():
        return int(value)
    match = _APP_VERSION_CODE_RE.search(value)
    if match:
        return int(match.group(1))
    match = _APP_VERSION_TOKEN_RE.search(value)
    if match:
        return int(match.group(1))
    return 0


def yongcha_pay_group_round_name(crew_member, round_no):
    if round_no not in (1, 2, 3):
        return ""
    pay_group = getattr(crew_member, "yongcha_pay_group", None)
    if not pay_group:
        return ""

    base_pay = _positive_decimal(getattr(pay_group, f"round_{round_no}_base_pay", 0))
    base_households = int(getattr(pay_group, f"round_{round_no}_base_households", 0) or 0)
    extra_pay = _positive_decimal(getattr(pay_group, f"round_{round_no}_extra_household_pay", 0))
    if base_pay <= 0 and base_households <= 0 and extra_pay <= 0:
        return ""
    return str(getattr(pay_group, "name", "") or "")


def yongcha_pay_group_round_detail(crew_member, round_no):
    if round_no not in (1, 2, 3):
        return None
    pay_group = getattr(crew_member, "yongcha_pay_group", None)
    if not pay_group:
        return None

    base_pay = _positive_decimal(getattr(pay_group, f"round_{round_no}_base_pay", 0))
    base_households = int(getattr(pay_group, f"round_{round_no}_base_households", 0) or 0)
    extra_pay = _positive_decimal(getattr(pay_group, f"round_{round_no}_extra_household_pay", 0))
    if base_pay <= 0 and base_households <= 0 and extra_pay <= 0:
        return None
    return {
        "name": str(getattr(pay_group, "name", "") or ""),
        "base_pay": int(base_pay),
        "base_households": base_households,
        "extra_household_pay": int(extra_pay),
        "exclude_base_pay_on_multi_round": bool(
            getattr(pay_group, "exclude_base_pay_on_multi_round", False)
        ),
    }


def yongcha_pay_group_round_extra_pay(crew_member, round_no):
    if round_no not in (1, 2, 3):
        return Decimal("0")
    pay_group = getattr(crew_member, "yongcha_pay_group", None)
    if not pay_group:
        return Decimal("0")
    return _positive_decimal(getattr(pay_group, f"round_{round_no}_extra_household_pay", 0))


class CrewMemberSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True, default="")
    team_code = serializers.CharField(source="team.code", read_only=True, default="")
    partner_name = serializers.CharField(source="partner.name", read_only=True, default="")
    yongcha_pay_group_name = serializers.CharField(source="yongcha_pay_group.name", read_only=True, default="")
    yongcha_pay_group_round_1_name = serializers.SerializerMethodField()
    yongcha_pay_group_round_2_name = serializers.SerializerMethodField()
    yongcha_pay_group_round_3_name = serializers.SerializerMethodField()
    yongcha_pay_group_round_1_detail = serializers.SerializerMethodField()
    yongcha_pay_group_round_2_detail = serializers.SerializerMethodField()
    yongcha_pay_group_round_3_detail = serializers.SerializerMethodField()
    regular_round_1_display_pay_price = serializers.SerializerMethodField()
    regular_round_2_display_pay_price = serializers.SerializerMethodField()
    regular_round_3_display_pay_price = serializers.SerializerMethodField()
    yongcha_round_1_display_pay_price = serializers.SerializerMethodField()
    yongcha_round_2_display_pay_price = serializers.SerializerMethodField()
    yongcha_round_3_display_pay_price = serializers.SerializerMethodField()
    app_version = serializers.SerializerMethodField()
    app_version_code = serializers.SerializerMethodField()
    has_mobile_app = serializers.SerializerMethodField()
    app_install_status = serializers.SerializerMethodField()
    app_install_status_label = serializers.SerializerMethodField()
    app_install_status_class_name = serializers.SerializerMethodField()

    class Meta:
        model = CrewMember
        fields = [
            "id",
            "code",
            "name",
            "phone",
            "vehicle_number",
            "pay_price",
            "yongcha_pay_price",
            "yongcha_pay_group",
            "yongcha_pay_group_name",
            "yongcha_pay_group_round_1_name",
            "yongcha_pay_group_round_2_name",
            "yongcha_pay_group_round_3_name",
            "yongcha_pay_group_round_1_detail",
            "yongcha_pay_group_round_2_detail",
            "yongcha_pay_group_round_3_detail",
            "regular_round_1_base_pay",
            "regular_round_2_base_pay",
            "regular_round_3_base_pay",
            "personal_round_1_yongcha_pay_price",
            "personal_round_2_yongcha_pay_price",
            "personal_round_3_yongcha_pay_price",
            "round_1_is_yongcha",
            "round_2_is_yongcha",
            "round_3_is_yongcha",
            "regular_round_1_display_pay_price",
            "regular_round_2_display_pay_price",
            "regular_round_3_display_pay_price",
            "yongcha_round_1_display_pay_price",
            "yongcha_round_2_display_pay_price",
            "yongcha_round_3_display_pay_price",
            "bank_name",
            "bank_account_number",
            "bank_account_holder",
            "vehicle_inspection_date",
            "app_version",
            "app_version_code",
            "has_mobile_app",
            "app_install_status",
            "app_install_status_label",
            "app_install_status_class_name",
            "team",
            "team_name",
            "team_code",
            "partner",
            "partner_name",
            "region",
            "is_active",
            "is_new",
            "is_yongcha",
            "two_insurance_percent",
            "note",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["code", "team", "created_at", "updated_at"]

    def _member_override(self, obj, round_no):
        return _positive_decimal(getattr(obj, f"personal_round_{round_no}_yongcha_pay_price", 0))

    def _team_regular(self, obj, round_no):
        team = getattr(obj, "team", None)
        if not team:
            return Decimal("3000")
        value = _positive_decimal(getattr(team, f"round_{round_no}_yongcha_pay_price", 0))
        if value > 0:
            return value
        general = _positive_decimal(getattr(team, "yongcha_pay_price", 0))
        return general if general > 0 else Decimal("3000")

    def _team_yongcha(self, obj, round_no):
        team = getattr(obj, "team", None)
        if not team:
            return Decimal("3000")
        value = _positive_decimal(getattr(team, f"yongcha_round_{round_no}_pay_price", 0))
        if value > 0:
            return value
        general = _positive_decimal(getattr(obj, "yongcha_pay_price", 0))
        if general > 0:
            return general
        team_general = _positive_decimal(getattr(team, "yongcha_pay_price", 0))
        return team_general if team_general > 0 else Decimal("3000")

    def _regular_display(self, obj, round_no):
        override = self._member_override(obj, round_no)
        return int(override if override > 0 else self._team_regular(obj, round_no))

    def _yongcha_display(self, obj, round_no):
        group_extra = yongcha_pay_group_round_extra_pay(obj, round_no)
        if group_extra > 0:
            return int(group_extra)
        override = self._member_override(obj, round_no)
        return int(override if override > 0 else self._team_yongcha(obj, round_no))

    def get_regular_round_1_display_pay_price(self, obj):
        return self._regular_display(obj, 1)

    def get_regular_round_2_display_pay_price(self, obj):
        return self._regular_display(obj, 2)

    def get_regular_round_3_display_pay_price(self, obj):
        return self._regular_display(obj, 3)

    def get_yongcha_round_1_display_pay_price(self, obj):
        return self._yongcha_display(obj, 1)

    def get_yongcha_round_2_display_pay_price(self, obj):
        return self._yongcha_display(obj, 2)

    def get_yongcha_round_3_display_pay_price(self, obj):
        return self._yongcha_display(obj, 3)

    def get_yongcha_pay_group_round_1_name(self, obj):
        return yongcha_pay_group_round_name(obj, 1)

    def get_yongcha_pay_group_round_2_name(self, obj):
        return yongcha_pay_group_round_name(obj, 2)

    def get_yongcha_pay_group_round_3_name(self, obj):
        return yongcha_pay_group_round_name(obj, 3)

    def get_yongcha_pay_group_round_1_detail(self, obj):
        return yongcha_pay_group_round_detail(obj, 1)

    def get_yongcha_pay_group_round_2_detail(self, obj):
        return yongcha_pay_group_round_detail(obj, 2)

    def get_yongcha_pay_group_round_3_detail(self, obj):
        return yongcha_pay_group_round_detail(obj, 3)

    def _optional_related(self, obj, related_name):
        try:
            return getattr(obj, related_name, None)
        except ObjectDoesNotExist:
            return None

    def _app_version(self, obj):
        live_status = self._optional_related(obj, "live_work_status")
        mobile_user = self._optional_related(obj, "mobile_app_user")
        return (
            (getattr(live_status, "last_app_version", "") if live_status else "")
            or (getattr(mobile_user, "last_app_version", "") if mobile_user else "")
            or ""
        )

    def _has_mobile_app(self, obj):
        mobile_user = self._optional_related(obj, "mobile_app_user")
        return bool(mobile_user or self._app_version(obj))

    def _app_install_status(self, obj):
        if not self._has_mobile_app(obj):
            return "not_installed"

        latest_code = int(self.context.get("latest_mobile_app_version_code") or 0)
        version_code = parse_app_version_code(self._app_version(obj))
        if latest_code > 0 and (version_code <= 0 or version_code < latest_code):
            return "update_required"
        return "installed"

    def get_app_version(self, obj):
        return self._app_version(obj)

    def get_app_version_code(self, obj):
        return parse_app_version_code(self._app_version(obj))

    def get_has_mobile_app(self, obj):
        return self._has_mobile_app(obj)

    def get_app_install_status(self, obj):
        return self._app_install_status(obj)

    def get_app_install_status_label(self, obj):
        status = self._app_install_status(obj)
        return {
            "installed": "예",
            "not_installed": "아니오",
            "update_required": "업데이트 필요",
        }.get(status, "-")

    def get_app_install_status_class_name(self, obj):
        status = self._app_install_status(obj)
        return {
            "installed": "bg-green-50 text-green-700 border border-green-200",
            "not_installed": "bg-gray-100 text-gray-500 border border-gray-200",
            "update_required": "bg-amber-50 text-amber-700 border border-amber-200",
        }.get(status, "bg-gray-100 text-gray-500 border border-gray-200")


class YongchaPayGroupSerializer(serializers.ModelSerializer):
    MONEY_FIELDS = (
        "round_1_base_pay",
        "round_1_extra_household_pay",
        "round_2_base_pay",
        "round_2_extra_household_pay",
        "round_3_base_pay",
        "round_3_extra_household_pay",
    )
    HOUSEHOLD_FIELDS = (
        "round_1_base_households",
        "round_2_base_households",
        "round_3_base_households",
    )

    class Meta:
        model = YongchaPayGroup
        fields = [
            "id",
            "company_app",
            "name",
            "round_1_base_pay",
            "round_1_base_households",
            "round_1_extra_household_pay",
            "round_2_base_pay",
            "round_2_base_households",
            "round_2_extra_household_pay",
            "round_3_base_pay",
            "round_3_base_households",
            "round_3_extra_household_pay",
            "exclude_base_pay_on_multi_round",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["company_app", "created_at", "updated_at"]

    def validate(self, attrs):
        for field in self.MONEY_FIELDS:
            if field not in attrs:
                continue
            try:
                value = Decimal(str(attrs.get(field) or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            except Exception as exc:
                raise serializers.ValidationError({field: "0 이상의 정수 원 단위로 입력하세요."}) from exc
            if value < 0:
                raise serializers.ValidationError({field: "0 이상의 정수 원 단위로 입력하세요."})
            attrs[field] = value

        for field in self.HOUSEHOLD_FIELDS:
            if field not in attrs:
                continue
            try:
                value = int(Decimal(str(attrs.get(field) or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            except Exception as exc:
                raise serializers.ValidationError({field: "0 이상의 정수로 입력하세요."}) from exc
            if value < 0:
                raise serializers.ValidationError({field: "0 이상의 정수로 입력하세요."})
            attrs[field] = value
        return attrs


class OvertimeSettingSerializer(serializers.ModelSerializer):
    crew_member_detail = CrewMemberSerializer(source="crew_member", read_only=True)

    class Meta:
        model = OvertimeSetting
        fields = [
            "id",
            "dispatch_upload",
            "crew_member",
            "crew_member_detail",
            "is_overtime",
            "overtime_cost",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
