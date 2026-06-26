from rest_framework import serializers

from .models import PointItem, PointRedemption, PointTransaction
from .services import (
    get_available_points,
    get_pending_redemption_points,
    get_point_balance,
    get_point_item_by_key,
)


class PointRedemptionSerializer(serializers.ModelSerializer):
    crew_name = serializers.CharField(source="crew_member.name", read_only=True)
    team_id = serializers.IntegerField(source="crew_member.team_id", read_only=True)
    team_name = serializers.CharField(source="crew_member.team.name", read_only=True, default="")
    team_code = serializers.CharField(source="crew_member.team.code", read_only=True, default="")

    class Meta:
        model = PointRedemption
        fields = [
            "id",
            "crew_member",
            "crew_name",
            "team_id",
            "team_name",
            "team_code",
            "item_key",
            "item_name",
            "cost_points",
            "status",
            "requested_at",
            "confirmed_at",
            "note",
        ]


class PointTransactionSerializer(serializers.ModelSerializer):
    redemption_item_name = serializers.CharField(source="redemption.item_name", read_only=True, default="")

    class Meta:
        model = PointTransaction
        fields = [
            "id",
            "points",
            "kind",
            "memo",
            "work_date",
            "tracking_session",
            "redemption",
            "redemption_item_name",
            "created_at",
        ]


class CrewPointSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    code = serializers.CharField()
    vehicle_number = serializers.CharField(allow_blank=True)
    team_id = serializers.IntegerField(allow_null=True)
    team_code = serializers.CharField(allow_blank=True)
    team_name = serializers.CharField(allow_blank=True)
    balance = serializers.IntegerField()
    pending_points = serializers.IntegerField()
    available_points = serializers.IntegerField()
    pending_redemptions = PointRedemptionSerializer(many=True)


class SetPointBalanceSerializer(serializers.Serializer):
    balance = serializers.IntegerField(min_value=0)
    memo = serializers.CharField(required=False, allow_blank=True, max_length=255)


class PointItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointItem
        fields = [
            "id",
            "key",
            "name",
            "cost_points",
            "sort_order",
            "is_active",
        ]


class PointItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointItem
        fields = [
            "id",
            "key",
            "name",
            "cost_points",
            "sort_order",
            "is_active",
        ]

    def validate_key(self, value):
        value = str(value or "").strip().lower().replace(" ", "_")
        if not value:
            raise serializers.ValidationError("항목 키를 입력해주세요.")
        return value


class MobileRedeemPointSerializer(serializers.Serializer):
    item_key = serializers.CharField(max_length=64)

    def validate_item_key(self, value):
        item = get_point_item_by_key(value, active_only=True)
        if not item:
            raise serializers.ValidationError("사용 가능한 포인트 상점 항목이 아닙니다.")
        return item.key


def serialize_crew_point_summary(crew):
    pending = list(
        PointRedemption.objects.filter(
            crew_member=crew,
            status=PointRedemption.Status.PENDING,
        ).order_by("-requested_at", "-id")
    )
    return {
        "id": crew.id,
        "name": crew.name,
        "code": crew.code,
        "vehicle_number": crew.vehicle_number or "",
        "team_id": crew.team_id,
        "team_code": crew.team.code if crew.team else "",
        "team_name": crew.team.name if crew.team else "",
        "balance": get_point_balance(crew),
        "pending_points": get_pending_redemption_points(crew),
        "available_points": get_available_points(crew),
        "pending_redemptions": PointRedemptionSerializer(pending, many=True).data,
    }
