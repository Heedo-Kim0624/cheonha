from rest_framework import serializers
from .models import Settlement, SettlementDetail


class SettlementDetailSerializer(serializers.ModelSerializer):
    crew_member_name = serializers.CharField(source='crew_member.name', read_only=True)
    crew_member_code = serializers.CharField(source='crew_member.code', read_only=True)

    class Meta:
        model = SettlementDetail
        fields = [
            'id', 'crew_member', 'crew_member_code', 'crew_member_name',
            'region', 'delivery_type', 'boxes', 'receive_amount', 'pay_amount',
            'overtime_cost', 'profit', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class SettlementSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True)
    confirmed_by_name = serializers.CharField(source='confirmed_by.get_full_name', read_only=True)
    details = SettlementDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Settlement
        fields = [
            'id', 'period_start', 'period_end', 'team', 'team_name',
            'status', 'total_receive', 'total_pay', 'total_overtime', 'total_profit',
            'confirmed_by', 'confirmed_by_name', 'confirmed_at', 'note',
            'details', 'created_at', 'updated_at'
        ]
        read_only_fields = ['confirmed_by', 'confirmed_at', 'created_at', 'updated_at']


class SettlementCreateSerializer(serializers.ModelSerializer):
    """정산 생성 serializer"""

    class Meta:
        model = Settlement
        fields = ['period_start', 'period_end', 'team', 'note']


class SettlementConfirmSerializer(serializers.Serializer):
    """정산 확정 serializer"""
    settlement_id = serializers.IntegerField()
