from rest_framework import serializers
from .models import SettlementInquiry, InquiryMessage


class InquiryMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InquiryMessage
        fields = ['id', 'author_type', 'author_name', 'content', 'created_at']
        read_only_fields = ['created_at']


class SettlementInquirySerializer(serializers.ModelSerializer):
    messages = InquiryMessageSerializer(many=True, read_only=True)
    crew_member_name = serializers.CharField(source='crew_member.name', read_only=True, default='')

    class Meta:
        model = SettlementInquiry
        fields = [
            'id', 'crew_member', 'crew_member_name', 'crew_name',
            'team', 'team_name', 'dispatch_date',
            'original_boxes', 'original_pay_price', 'original_adjustment', 'original_total',
            'boxes', 'pay_price', 'is_overtime', 'adjustment_amount', 'total_amount',
            'status', 'last_by',
            'messages', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'last_by', 'status']
