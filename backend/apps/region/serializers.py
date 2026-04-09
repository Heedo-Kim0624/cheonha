from rest_framework import serializers
from .models import Region, RegionPrice, PriceHistory


class RegionPriceSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegionPrice
        fields = ['id', 'delivery_type', 'receive_price', 'pay_price', 'start_date', 'end_date']


class RegionSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True)
    prices = RegionPriceSimpleSerializer(many=True, read_only=True)

    class Meta:
        model = Region
        fields = ['id', 'code', 'team', 'team_name', 'name', 'is_active', 'note', 'prices', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class PriceHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)

    class Meta:
        model = PriceHistory
        fields = ['id', 'field_changed', 'old_value', 'new_value', 'changed_by', 'changed_by_name', 'changed_at']
        read_only_fields = ['changed_at', 'changed_by', 'changed_by_name']


class RegionPriceSerializer(serializers.ModelSerializer):
    region_detail = RegionSerializer(source='region', read_only=True)
    histories = PriceHistorySerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = RegionPrice
        fields = [
            'id', 'region', 'region_detail', 'delivery_type', 'receive_price',
            'pay_price', 'start_date', 'end_date', 'histories',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = ['created_at', 'updated_at']
