from rest_framework import serializers


class KPISerializer(serializers.Serializer):
    """KPI 데이터 serializer"""
    total_settlements = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=0)
    total_paid = serializers.DecimalField(max_digits=12, decimal_places=0)
    total_profit = serializers.DecimalField(max_digits=12, decimal_places=0)
    active_crews = serializers.IntegerField()
    active_regions = serializers.IntegerField()


class RevenueByRegionSerializer(serializers.Serializer):
    """권역별 수익 serializer"""
    region = serializers.CharField()
    revenue = serializers.DecimalField(max_digits=12, decimal_places=0)
    count = serializers.IntegerField()


class SettlementSummarySerializer(serializers.Serializer):
    """정산 요약 serializer"""
    period = serializers.CharField()
    total_receive = serializers.DecimalField(max_digits=12, decimal_places=0)
    total_pay = serializers.DecimalField(max_digits=12, decimal_places=0)
    total_profit = serializers.DecimalField(max_digits=12, decimal_places=0)
