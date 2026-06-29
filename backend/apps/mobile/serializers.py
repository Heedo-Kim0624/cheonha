from rest_framework import serializers

from .app_messages import APP_MESSAGE_DEFAULTS, APP_MESSAGE_SECTIONS
from .models import MobileAppUser


def validate_password_pin(value):
    value = str(value or "").strip()
    if len(value) != 4 or not value.isdigit():
        raise serializers.ValidationError("비밀번호는 4자리 숫자여야 합니다.")
    return value


def _has_initial_field(serializer, key):
    return key in getattr(serializer, "initial_data", {})


def _validate_signup_agreements(serializer, attrs):
    if not attrs["agree_privacy_policy"]:
        raise serializers.ValidationError(
            {"agree_privacy_policy": "개인정보처리방침 동의가 필요합니다."}
        )
    if not attrs["agree_terms"]:
        raise serializers.ValidationError(
            {"agree_terms": "이용약관 동의가 필요합니다."}
        )
    if _has_initial_field(serializer, "agree_data_processing") and not attrs.get(
        "agree_data_processing"
    ):
        raise serializers.ValidationError(
            {"agree_data_processing": "제3자 정보제공 동의가 필요합니다."}
        )
    if (
        not _has_initial_field(serializer, "agree_data_processing")
        and _has_initial_field(serializer, "agree_third_party_information")
        and not attrs.get("agree_third_party_information")
    ):
        raise serializers.ValidationError(
            {"agree_third_party_information": "제3자 정보제공 동의가 필요합니다."}
        )
    if _has_initial_field(serializer, "agree_location_terms") and not attrs.get(
        "agree_location_terms"
    ):
        raise serializers.ValidationError(
            {"agree_location_terms": "위치정보기반 서비스 이용약관 동의가 필요합니다."}
        )
    return attrs


class MobileRegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50)
    team_code = serializers.CharField(max_length=1)
    password = serializers.CharField(max_length=4, min_length=4)
    password_confirm = serializers.CharField(max_length=4, min_length=4)
    vehicle_number = serializers.CharField(max_length=20)
    app_version = serializers.CharField(max_length=40, required=False, allow_blank=True)
    agree_privacy_policy = serializers.BooleanField()
    agree_terms = serializers.BooleanField()
    agree_data_processing = serializers.BooleanField(required=False, default=None)
    agree_third_party_information = serializers.BooleanField(required=False, default=None)
    agree_location_terms = serializers.BooleanField(required=False, default=None)
    agree_marketing_event = serializers.BooleanField(required=False, default=False)

    def validate_team_code(self, value):
        return str(value or "").strip().upper()

    def validate_password(self, value):
        return validate_password_pin(value)

    def validate_password_confirm(self, value):
        return validate_password_pin(value)

    def validate_vehicle_number(self, value):
        value = str(value or "").strip()
        if not value:
            raise serializers.ValidationError("차량번호를 입력해 주세요.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "비밀번호 확인이 일치하지 않습니다."}
            )
        return _validate_signup_agreements(self, attrs)


class MobileSignupCompleteSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=4, min_length=4)
    password_confirm = serializers.CharField(max_length=4, min_length=4)
    vehicle_number = serializers.CharField(max_length=20)
    app_version = serializers.CharField(max_length=40, required=False, allow_blank=True)
    agree_privacy_policy = serializers.BooleanField()
    agree_terms = serializers.BooleanField()
    agree_data_processing = serializers.BooleanField(required=False, default=None)
    agree_third_party_information = serializers.BooleanField(required=False, default=None)
    agree_location_terms = serializers.BooleanField(required=False, default=None)
    agree_marketing_event = serializers.BooleanField(required=False, default=False)

    def validate_password(self, value):
        return validate_password_pin(value)

    def validate_password_confirm(self, value):
        return validate_password_pin(value)

    def validate_vehicle_number(self, value):
        value = str(value or "").strip()
        if not value:
            raise serializers.ValidationError("차량번호를 입력해 주세요.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "비밀번호 확인이 일치하지 않습니다."}
            )
        return _validate_signup_agreements(self, attrs)


class MobileLoginSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50)
    team_code = serializers.CharField(max_length=1)
    password = serializers.CharField(max_length=4, min_length=4)
    app_version = serializers.CharField(max_length=40, required=False, allow_blank=True)

    def validate_team_code(self, value):
        return str(value or "").strip().upper()

    def validate_password(self, value):
        return validate_password_pin(value)


class MobilePasswordChangeSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=4, min_length=4)
    password_confirm = serializers.CharField(max_length=4, min_length=4)
    vehicle_number = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
    )

    def validate_password(self, value):
        return validate_password_pin(value)

    def validate_password_confirm(self, value):
        return validate_password_pin(value)

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "비밀번호 확인이 일치하지 않습니다."}
            )
        return attrs


class MobileAppUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MobileAppUser
        fields = [
            "id",
            "name",
            "team_code",
            "status",
            "requested_at",
            "approved_at",
            "signup_completed",
            "signup_completed_at",
            "privacy_policy_agreed_at",
            "terms_agreed_at",
            "third_party_information_agreed_at",
            "location_terms_agreed_at",
            "marketing_event_agreed_at",
            "last_app_version",
        ]


class MobileApprovalActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])


class SettlementDaySerializer(serializers.Serializer):
    class RoundSummarySerializer(serializers.Serializer):
        round_no = serializers.IntegerField(allow_null=True, required=False)
        box_count = serializers.IntegerField(required=False, default=0)
        household_count = serializers.IntegerField(required=False, default=0)
        amount = serializers.IntegerField(required=False, default=0)
        is_yongcha = serializers.BooleanField(required=False, default=False)

    date = serializers.DateField()
    box_count = serializers.IntegerField()
    adjustment_amount = serializers.IntegerField(required=False, default=0)
    amount = serializers.IntegerField()
    round_summaries = RoundSummarySerializer(many=True, required=False, default=list)
    inquiry_updated_at = serializers.DateTimeField(
        allow_null=True,
        required=False,
    )
    inquiry_status = serializers.ChoiceField(
        choices=["pending", "answered"],
        allow_null=True,
        required=False,
    )


class MonthlySettlementSerializer(serializers.Serializer):
    days = SettlementDaySerializer(many=True)
    total_boxes = serializers.IntegerField()
    total_amount = serializers.IntegerField()


class MobileProfileSerializer(serializers.Serializer):
    name = serializers.CharField()
    team_code = serializers.CharField()
    team_name = serializers.CharField()
    vehicle_number = serializers.CharField()
    bank_name = serializers.CharField()
    bank_account_number = serializers.CharField()
    vehicle_inspection_date = serializers.DateField(allow_null=True)
    requires_password_change = serializers.BooleanField()
    signup_completed = serializers.BooleanField(required=False)
    privacy_policy_agreed_at = serializers.DateTimeField(
        allow_null=True,
        required=False,
    )
    terms_agreed_at = serializers.DateTimeField(
        allow_null=True,
        required=False,
    )
    third_party_information_agreed_at = serializers.DateTimeField(
        allow_null=True,
        required=False,
    )
    location_terms_agreed_at = serializers.DateTimeField(
        allow_null=True,
        required=False,
    )
    marketing_event_agreed_at = serializers.DateTimeField(
        allow_null=True,
        required=False,
    )


class MobileVehicleNumberSerializer(serializers.Serializer):
    vehicle_number = serializers.CharField(max_length=20)

    def validate_vehicle_number(self, value):
        value = str(value or "").strip()
        if not value:
            raise serializers.ValidationError("차량번호를 입력해 주세요.")
        return value


class MobilePayrollAccountSerializer(serializers.Serializer):
    bank_name = serializers.CharField(max_length=50)
    bank_account_number = serializers.CharField(max_length=100)

    def validate_bank_name(self, value):
        value = str(value or "").strip()
        if not value:
            raise serializers.ValidationError("은행명을 입력해 주세요.")
        return value

    def validate_bank_account_number(self, value):
        value = str(value or "").strip()
        if not value:
            raise serializers.ValidationError("계좌번호를 입력해 주세요.")
        return value


class MobileVehicleInspectionDateSerializer(serializers.Serializer):
    vehicle_inspection_date = serializers.DateField()


class MobileSettlementInquiryRequestSerializer(serializers.Serializer):
    date = serializers.DateField()


class MobileSettlementInquiryCommentSerializer(serializers.Serializer):
    date = serializers.DateField()
    content = serializers.CharField()

    def validate_content(self, value):
        value = str(value or "").strip()
        if not value:
            raise serializers.ValidationError("문의 내용을 입력해 주세요.")
        return value


class MobileSettlementInquiryReadSerializer(serializers.Serializer):
    inquiry_id = serializers.IntegerField()


class MobileWorkSessionUploadSerializer(serializers.Serializer):
    csv_content = serializers.CharField()
    file_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    vehicle_number = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
    )
    app_version = serializers.CharField(max_length=40, required=False, allow_blank=True)

    def validate_csv_content(self, value):
        value = str(value or "")
        if not value.strip():
            raise serializers.ValidationError("업로드할 CSV 내용이 없습니다.")
        return value


class MobileWorkSessionLiveSerializer(serializers.Serializer):
    vehicle_number = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
    )
    background_location_granted = serializers.BooleanField(required=False)
    app_version = serializers.CharField(max_length=40, required=False, allow_blank=True)


class MobileAppConfigSerializer(serializers.Serializer):
    messages = serializers.DictField(
        child=serializers.CharField(allow_blank=True),
        default=dict,
    )
    updated_at = serializers.DateTimeField(required=False, allow_null=True)


class MobileAdminAppConfigSerializer(serializers.Serializer):
    sections = serializers.ListField(required=False)
    messages = serializers.DictField(
        child=serializers.CharField(allow_blank=True),
        default=dict,
    )
    updated_at = serializers.DateTimeField(required=False, allow_null=True)


class MobileAdminAppConfigWriteSerializer(serializers.Serializer):
    messages = serializers.DictField(
        child=serializers.CharField(allow_blank=True),
        default=dict,
    )

    def validate_messages(self, value):
        cleaned = {}
        for key, field_value in (value or {}).items():
            if key not in APP_MESSAGE_DEFAULTS:
                continue
            cleaned[key] = str(field_value or "")
        return cleaned


def get_mobile_app_message_sections():
    return APP_MESSAGE_SECTIONS
