from rest_framework import serializers
from .models import MobileAppUser


def validate_password_pin(value):
    value = str(value or "").strip()
    if len(value) != 4 or not value.isdigit():
        raise serializers.ValidationError("비밀번호는 4자리 숫자여야 합니다.")
    return value


class MobileRegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50)
    team_code = serializers.CharField(max_length=1)

    def validate_team_code(self, value):
        return value.upper()


class MobileLoginSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50)
    team_code = serializers.CharField(max_length=1)
    password = serializers.CharField(max_length=4, min_length=4)

    def validate_team_code(self, value):
        return value.upper()

    def validate_password(self, value):
        return validate_password_pin(value)


class MobilePasswordChangeSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=4, min_length=4)
    password_confirm = serializers.CharField(max_length=4, min_length=4)

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
        ]


class MobileApprovalActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])


class SettlementDaySerializer(serializers.Serializer):
    date = serializers.DateField()
    box_count = serializers.IntegerField()
    amount = serializers.IntegerField()


class MonthlySettlementSerializer(serializers.Serializer):
    days = SettlementDaySerializer(many=True)
    total_boxes = serializers.IntegerField()
    total_amount = serializers.IntegerField()


class MobileProfileSerializer(serializers.Serializer):
    name = serializers.CharField()
    team_code = serializers.CharField()
    team_name = serializers.CharField()
