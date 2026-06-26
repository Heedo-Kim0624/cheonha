from rest_framework import serializers
from .models import Territory, TerritoryBoxRecord


class TerritorySerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True, default='')
    yongcha_delivery_count = serializers.SerializerMethodField()

    class Meta:
        model = Territory
        fields = [
            'id', 'code', 'group_letter', 'team', 'team_name',
            'geometry', 'centroid_lat', 'centroid_lon', 'color', 'note',
            'yongcha_delivery_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['group_letter', 'centroid_lat', 'centroid_lon',
                            'created_at', 'updated_at']

    def get_yongcha_delivery_count(self, obj):
        from apps.settlement.models import SettlementDetail

        return SettlementDetail.objects.filter(
            region=obj.code,
            is_yongcha=True,
        ).count()


class TerritoryBoxRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = TerritoryBoxRecord
        fields = ['id', 'territory', 'date', 'box_count', 'is_split']
