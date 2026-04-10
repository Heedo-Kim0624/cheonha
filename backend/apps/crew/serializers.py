from rest_framework import serializers
from .models import CrewMember, OvertimeSetting


class CrewMemberSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True, default='')
    team_code = serializers.CharField(source='team.code', read_only=True, default='')
    partner_name = serializers.CharField(source='partner.name', read_only=True, default='')

    class Meta:
        model = CrewMember
        fields = [
            'id', 'code', 'name', 'phone', 'vehicle_number', 'pay_price',
            'team', 'team_name', 'team_code', 'partner', 'partner_name',
            'region', 'is_active', 'is_new', 'note',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['code', 'team', 'created_at', 'updated_at']


class OvertimeSettingSerializer(serializers.ModelSerializer):
    crew_member_detail = CrewMemberSerializer(source='crew_member', read_only=True)

    class Meta:
        model = OvertimeSetting
        fields = [
            'id', 'dispatch_upload', 'crew_member', 'crew_member_detail',
            'is_overtime', 'overtime_cost', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
